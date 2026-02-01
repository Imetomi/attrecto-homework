"""
LLM Gateway with rate limiting and retry logic.
Prevents hitting Azure OpenAI rate limits (50 req/min, 50K tokens/min).
"""

import time
import json
from typing import Optional, Dict, Any
from collections import deque
from datetime import datetime, timedelta
from openai import AzureOpenAI
from openai import RateLimitError, APIError, APIConnectionError

import config


class RateLimiter:
    """
    Token bucket rate limiter for API requests and tokens.
    Tracks both requests per minute and tokens per minute.
    """

    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_minute: int
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute

        # Track request timestamps in the last minute
        self.request_times = deque()

        # Track token usage in the last minute
        self.token_usage = deque()  # [(timestamp, token_count)]

    def _clean_old_entries(self):
        """Remove entries older than 1 minute."""
        cutoff_time = datetime.now() - timedelta(minutes=1)

        # Clean request times
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()

        # Clean token usage
        while self.token_usage and self.token_usage[0][0] < cutoff_time:
            self.token_usage.popleft()

    def _get_current_request_count(self) -> int:
        """Get number of requests in the last minute."""
        self._clean_old_entries()
        return len(self.request_times)

    def _get_current_token_count(self) -> int:
        """Get total tokens used in the last minute."""
        self._clean_old_entries()
        return sum(tokens for _, tokens in self.token_usage)

    def wait_if_needed(self, estimated_tokens: int = 1000):
        """
        Wait if necessary to avoid hitting rate limits.

        Args:
            estimated_tokens: Estimated tokens for the upcoming request
        """
        self._clean_old_entries()

        # Check request limit
        if self._get_current_request_count() >= self.requests_per_minute:
            wait_time = self._calculate_wait_time_for_requests()
            if wait_time > 0:
                print(f"⏱️  Rate limit: waiting {wait_time:.1f}s for request quota...")
                time.sleep(wait_time)
                self._clean_old_entries()

        # Check token limit
        current_tokens = self._get_current_token_count()
        if current_tokens + estimated_tokens >= self.tokens_per_minute:
            wait_time = self._calculate_wait_time_for_tokens()
            if wait_time > 0:
                print(f"⏱️  Rate limit: waiting {wait_time:.1f}s for token quota...")
                time.sleep(wait_time)
                self._clean_old_entries()

    def _calculate_wait_time_for_requests(self) -> float:
        """Calculate how long to wait for request quota to free up."""
        if not self.request_times:
            return 0

        oldest_request = self.request_times[0]
        time_since_oldest = (datetime.now() - oldest_request).total_seconds()

        # Wait until oldest request expires (falls out of 1-minute window)
        return max(0, 60 - time_since_oldest + 0.5)  # +0.5s buffer

    def _calculate_wait_time_for_tokens(self) -> float:
        """Calculate how long to wait for token quota to free up."""
        if not self.token_usage:
            return 0

        oldest_token_usage = self.token_usage[0][0]
        time_since_oldest = (datetime.now() - oldest_token_usage).total_seconds()

        return max(0, 60 - time_since_oldest + 0.5)  # +0.5s buffer

    def record_request(self, tokens_used: int):
        """Record a completed request with its token usage."""
        now = datetime.now()
        self.request_times.append(now)
        self.token_usage.append((now, tokens_used))


class LLMGateway:
    """
    Gateway for Azure OpenAI API calls with rate limiting and retry logic.
    """

    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_KEY,
            api_version=config.AZURE_API_VERSION
        )

        self.rate_limiter = RateLimiter(
            requests_per_minute=config.RATE_LIMIT_REQUESTS_PER_MINUTE,
            tokens_per_minute=config.RATE_LIMIT_TOKENS_PER_MINUTE
        )

        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost_usd = 0.0

    def call_chat_completion(
        self,
        messages: list,
        temperature: float = config.TEMPERATURE,
        max_tokens: int = config.MAX_TOKENS,
        response_format: Optional[Dict[str, str]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call Azure OpenAI Chat Completion API with rate limiting and retries.

        Args:
            messages: List of message dicts [{role: content}]
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})
            max_retries: Maximum number of retry attempts

        Returns:
            Dict containing response content and usage stats

        Raises:
            Exception if all retries fail
        """
        # Estimate tokens for rate limiting (rough estimate)
        estimated_tokens = sum(len(str(m.get('content', ''))) // 4 for m in messages)
        estimated_tokens += max_tokens

        # Wait if needed to respect rate limits
        self.rate_limiter.wait_if_needed(estimated_tokens)

        for attempt in range(max_retries):
            try:
                # Build request parameters
                request_params = {
                    "model": config.AZURE_OPENAI_DEPLOYMENT,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                if response_format:
                    request_params["response_format"] = response_format

                # Make API call
                response = self.client.chat.completions.create(**request_params)

                # Extract response data
                content = response.choices[0].message.content
                usage = response.usage

                # Record usage
                total_tokens = usage.total_tokens
                self.rate_limiter.record_request(total_tokens)
                self.total_requests += 1
                self.total_tokens += total_tokens

                # Estimate cost (GPT-4 pricing: ~$0.03/1K input, ~$0.06/1K output)
                input_cost = (usage.prompt_tokens / 1000) * 0.03
                output_cost = (usage.completion_tokens / 1000) * 0.06
                self.total_cost_usd += input_cost + output_cost

                return {
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }

            except RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️  Rate limit hit, waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

            except (APIError, APIConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  API error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"API call failed after {max_retries} attempts: {str(e)}")

            except Exception as e:
                raise Exception(f"Unexpected error in API call: {str(e)}")

        raise Exception(f"Failed to complete API call after {max_retries} retries")

    def call_with_json_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Convenience method for JSON-formatted responses.

        Args:
            system_prompt: System message
            user_prompt: User message
            max_retries: Maximum retries

        Returns:
            Parsed JSON response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.call_chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
            max_retries=max_retries
        )

        try:
            parsed_json = json.loads(response["content"])
            return {
                "data": parsed_json,
                "usage": response["usage"]
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}\nContent: {response['content']}")

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost_usd, 2),
            "current_request_count": self.rate_limiter._get_current_request_count(),
            "current_token_count": self.rate_limiter._get_current_token_count()
        }

    def print_stats(self):
        """Print usage statistics."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("LLM GATEWAY STATISTICS")
        print("=" * 60)
        print(f"Total Requests:        {stats['total_requests']}")
        print(f"Total Tokens:          {stats['total_tokens']:,}")
        print(f"Estimated Cost:        ${stats['estimated_cost_usd']:.2f}")
        print(f"Current Request Count: {stats['current_request_count']}/{config.RATE_LIMIT_REQUESTS_PER_MINUTE}")
        print(f"Current Token Count:   {stats['current_token_count']:,}/{config.RATE_LIMIT_TOKENS_PER_MINUTE:,}")
        print("=" * 60)
