# FoxAI: AI-Driven Content and Image Creation

![FoxAI Demo] https://www.youtube.com/watch?v=cfp23UJBQD4
 
## Overview

Developed by Giovanni Venegas as a final project for CS50 at Harvard University, FoxAI is a web application that leverages AI to streamline content creation. It offers AI-powered text content generation and image creation.

## Features

- **AI-Driven Text Content**: Utilizes advanced NLP techniques for contextually relevant text content.
- **AI Image Generation**: Uses OpenAI's API for image generation from user descriptions.
- **Temporary Image Storage**: Allows users to review and download generated images for an hour.
- **Automated Image Deletion**: Optimizes storage by automatically deleting images older than one hour.

## Code Highlights

### `app.py` (Application Setup and Routes)

- **Flask Configuration**: Secure and efficient Flask app setup with session management.
- **Route Handling**: Manages endpoints for image generation, user authentication, and content management.
- **API Integration**: Securely accesses the OpenAI API key, ensuring sensitive data handling.

### `history.py` (Image Management)

- **Image Lifecycle Management**: Manages image storage, display, and automatic deletion.
- **Database Interaction**: Efficiently interacts with the PostgreSQL database for image data.

### `helpers.py` (Utility Functions)

- **API Key Retrieval**: Fetches the OpenAI API key from environment variables for security.
- **Database Connection**: Establishes secure connections for user and image data handling.
- **User Authentication**: Implements user security and access control through the `login_required` decorator.

## Technical Stack

- **Flask Framework**: Chosen for flexibility in web app development.
- **Environment Variable Management**: Secure handling of API keys and database credentials.
- **PostgreSQL Database**: Scalable and reliable for dynamic content management.

## Challenges and Solutions

- **API Integration**: Overcame initial challenges through robust error handling and response parsing.
- **Database Management**: Optimized SQL queries and session management for enhanced performance.
- **User Interface Design**: User-centered design approach ensured an intuitive and responsive interface.

## Conclusion and Future Plans

FoxAI simplifies content generation with AI. Future plans include expanding AI capabilities and enhancing user experience.

## Live Testing

To try FoxAI, visit [FoxAI Live](http://3.138.126.105/login).  
**Note**: Contact for secure testing access.

## Contact Information

For inquiries or collaborations, contact Giovanni Venegas:
- LinkedIn: [Giovanni Venegas](https://www.linkedin.com/in/giovannivenegas/)
- GitHub: [Giovanni's GitHub](https://github.com/Giovanniv)
- Email: [giovanni@askfoxai.com](mailto:giovanni@askfoxai.com)