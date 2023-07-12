<h1 align="center">Ultimate Threads Scraper</h1>

Welcome to the GitHub repository of Ultimate Threads Scraper , a robust Social Media Scraper designed to download content from the Threads.net platform by Meta. ✨

Introducing the elegant Thread Data Collection Software, designed for businesses, sales and marketing professionals, and researchers.

## Features 🚀

A Software that scrapes the following sections from threads:

- Fetch user's and thread's unique identifiers.
- Retrieve user's details, threads, and replies.
- Retrieve thread's details and its likers.
- Save the fetched data into CSV and JSON files.

## :file_folder: File Structure

- `base_interface.py`: Provides a basic interface for interacting with Threads.
- `threads_interface.py`: A public interface for the scraper with methods for fetching and saving data.

## :rocket: How to Use

Example:

1. Import the `ThreadsInterface` class from `threads_interface.py`.
2. Create an instance of the `ThreadsInterface` class.
3. Use the instance to call the methods for fetching and saving data.

## Output

1. **Scrape User ID**
    
    - Input: `username`
    - Output: `user_id`
    - Example:
        - Input: `john_doe`
        - Output: `12345`
2. **Scrape Thread ID**
    
    - Input: `url_id` (last part of a thread's URL)
    - Output: `thread_id`
    - Example:
        - Input: `CuXFPIeLLod`
        - Output: `54321`
3. **Fetch User**
    
    - Input: `user_id`
    - Output: User information in JSON format
    - Example:
        - Input: `12345`
        - Output: `{ "username": "john_doe", "email": "johndoe@example.com", "date_joined": "2022-01-01" }`
4. **Fetch User Threads**
    
    - Input: `user_id`
    - Output: List of threads posted by the user in JSON format
    - Example:
        - Input: `12345`
        - Output: `[{ "thread_id": "54321", "title": "My first thread", "date_posted": "2022-02-02" }, {...}]`
5. **Fetch User Replies**
    
    - Input: `user_id`
    - Output: List of replies posted by the user in JSON format
    - Example:
        - Input: `12345`
        - Output: `[{ "reply_id": "4321", "thread_id": "54321", "content": "Great thread!", "date_posted": "2022-02-03" }, {...}]`
6. **Fetch Thread**
    
    - Input: `thread_id`
    - Output: Thread information in JSON format
    - Example:
        - Input: `54321`
        - Output: `{ "title": "My first thread", "content": "Hello, world!", "date_posted": "2022-02-02" }`
7. **Fetch Thread Likers**
    
    - Input: `thread_id`
    - Output: List of users who liked the thread in JSON format
    - Example:
        - Input: `54321`
        - Output: `[{ "user_id": "12345", "username": "john_doe" }, {...}]`
8. **Generate Scraper Token**
    
    - Input: None
    - Output: A token for the Thread Scraper
    - Example:
        - Input: None
        - Output: `abc123def456ghi789`
