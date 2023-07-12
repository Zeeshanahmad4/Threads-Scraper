"""
Provide a public interface for the Threads.
"""
import json
import re
import requests
from base_interface import BaseThreadsInterface

import csv
import os
import pandas as pd


class ThreadsInterface(BaseThreadsInterface):
    """
    A public interface for interacting with Threads.

    Each unique endpoint requires a unique document ID, predefined by the developers.
    """
    THREADS_API_URL = 'https://www.threads.net/api/graphql'

    def __init__(self):
        """
        Initialize the object.
        """
        super().__init__()

        self.api_token = self._generate_api_token()
        self.default_headers = {
            'Authority': 'www.threads.net',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.threads.net',
            'Pragma': 'no-cache',
            'Sec-Fetch-Site': 'same-origin',
            'X-ASBD-ID': '129477',
            'X-FB-LSD': self.api_token,
            'X-IG-App-ID': '238260118697367',
        }

    def retrieve_user(self, user_id: int) -> dict:
        """
        Retrieve a user.

        Args:
            user_id (int): The user's unique identifier.

        Returns:
            The user as a dictionary.
        """
        headers = self.default_headers.copy()
        headers['X-FB-Friendly-Name'] = 'BarcelonaProfileRootQuery'

        response = requests.post(
            url=self.THREADS_API_URL,
            headers=headers,
            data={
                'lsd': self.api_token,
                'variables': json.dumps(
                    {
                        'userID': user_id,
                    }
                ),
                'doc_id': '23996318473300828',
            },
        )

        return response.json()

    def retrieve_user_threads(self, user_id: int) -> dict:
        """
        Retrieve a user's threads.

        Args:
            user_id (int): The user's unique identifier.

        Returns:
            The list of user's threads inside a dictionary.
        """
        headers = self.default_headers.copy()
        headers['X-FB-Friendly-Name'] = 'BarcelonaProfileThreadsTabQuery'

        response = requests.post(
            url=self.THREADS_API_URL,
            headers=headers,
            data={
                'lsd': self.api_token,
                'variables': json.dumps(
                    {
                        'userID': user_id,
                    }
                ),
                'doc_id': '6232751443445612',
            },
        )

        return response.json()

    def retrieve_user_replies(self, user_id: int) -> dict:
        """
        Retrieve a user's replies.

        Args:
            user_id (int): The user's unique identifier.

        Returns:
            The list of user's replies inside a dictionary.
        """
        headers = self.default_headers.copy()
        headers['X-FB-Friendly-Name'] = 'BarcelonaProfileRepliesTabQuery'

        response = requests.post(
            url=self.THREADS_API_URL,
            headers=headers,
            data={
                'lsd': self.api_token,
                'variables': json.dumps(
                    {
                        'userID': user_id,
                    }
                ),
                'doc_id': '6307072669391286',
            },
        )

        return response.json()

    def retrieve_thread(self, thread_id: int) -> dict:
        """
        Retrieve a thread.

        Args:
            thread_id (int): The thread's unique identifier.

        Returns:
            The thread as a dictionary.
        """
        headers = self.default_headers.copy()
        headers['X-FB-Friendly-Name'] = 'BarcelonaPostPageQuery'

        response = requests.post(
            url=self.THREADS_API_URL,
            headers=headers,
            data={
                'lsd': self.api_token,
                'variables': json.dumps(
                    {
                        'postID': thread_id,
                    }
                ),
                'doc_id': '5587632691339264',
            },
        )

        return response.json()

    def retrieve_thread_likers(self, thread_id: int) -> dict:
        """
        Retrieve the likers of a thread.

        Args:
            thread_id (int): The thread's unique identifier.

        Returns:
            The list of likers of the thread inside a dictionary.
        """
        response = requests.post(
            url=self.THREADS_API_URL,
            headers=self.default_headers,
            data={
                'lsd': self.api_token,
                'variables': json.dumps(
                    {
                        'mediaID': thread_id,
                    }
                ),
                'doc_id': '9360915773983802',
            },
        )

        return response.json()

    def _generate_api_token(self) -> str:
        """
        Generate a token for the Threads.

        The token, called `lsd` internally, is required for any request.
        For anonymous users, it is just generated automatically from the back-end and passed to the front-end.

        Returns:
            The token for the Threads as a string.
        """
        response = requests.get(
            url='https://www.instagram.com/instagram',
            headers=self.headers_for_html_fetching,
        )

        token_key_value = re.search(
            'LSD",\\[\\],{"token":"(.*?)"},\\d+\\]', response.text).group()
        token_key_value = token_key_value.replace('LSD",[],{"token":"', '')
        token = token_key_value.split('"')[0]

        return token

    def save_data_to_csv(self, data: dict
        """
        Save the provided data into a CSV file.

        Args:
            data (dict): The data to be saved.
            filename (str): The filename of the CSV file.
        """
        # Convert the dictionary to a DataFrame
        df = pd.DataFrame(data)

        # Check if file exists
        if os.path.isfile(filename):
            # If it exists, append without writing headers
            df.to_csv(filename, mode='a', header=False, index=False)
        else:
            # If it doesn't exist, write the DataFrame with headers
            df.to_csv(filename, index=False)

    def save_data_to_json(self, data: dict, filename: str):
        """
        Save the provided data into a JSON file.

        Args:
            data (dict): The data to be saved.
            filename (str): The filename of the JSON file.
        """
        with open(filename, 'a') as json_file:
            json.dump(data, json_file)
