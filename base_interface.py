"""
Provide a basic interface for the Threads.
"""
import re
import requests

class BaseThreadsInterface:
    """
    A basic interface for interacting with Threads.
    """

    def __init__(self):
        """
        Initialize the object.
        """
        self.headers_for_html_fetching = {
            'Authority': 'www.threads.net',
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                'q=0.8,application/signed-exchange;v=b3;q=0.7'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.threads.net',
            'Pragma': 'no-cache',
            'Referer': 'https://www.instagram.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15'
            ),
        }

    def retrieve_user_id(self, username: str) -> int:
        """
        Retrieve the unique identifier for a user.

        Args:
            username (str): The user's username.

        Returns:
            The user's unique identifier as an integer.
        """
        response = requests.get(
            url=f'https://www.instagram.com/{username}',
            headers=self.headers_for_html_fetching,
        )

        user_id_key_value = re.search('"user_id":"(\\d+)",', response.text).group()
        user_id = re.search('\\d+', user_id_key_value).group()

        return int(user_id)

    def retrieve_thread_id(self, url_id: str) -> int:
        """
        Retrieve the unique identifier for a thread.

        Args:
            url_id (str): The thread's URL identifier.

        Returns:
            The thread's unique identifier as an integer.
        """
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

        thread_id = 0

        for character in url_id:
            thread_id = (thread_id * 64) + alphabet.index(character)

        return thread_id
