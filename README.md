<h1 align="center">Ultimate Threads Scraper</h1>

Welcome to the GitHub repository of Ultimate Threads Scraper , a robust Social Media Scraper designed to download content from the novel Threads platform by Meta. ✨

Introducing the elegant Thread Data Collection Software, designed for businesses, sales and marketing professionals, and researchers.




<h1 align="center">Writing the code :) </h1>


## Features 🚀

A Software that scrapes the following sections from threads:

**User Profile/Account**

- **Get Identifier**: Retrieve the unique identifier for a user.
- **Get By Identifier**: Fetch user details based on their identifier.
- **Get Threads**: Retrieve the list of threads associated with a user.
- **Get Replies**: Get the replies made by a user.

**Thread**


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

- **Get Identifier**: Obtain the identifier for a specific thread.
- **Get By Identifier**: Fetch thread details based on its identifier.
- **Get Likers**: Get the users who have liked a particular thread.

**Save/Export to File CSV/Json**
