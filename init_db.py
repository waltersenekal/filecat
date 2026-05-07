#!/usr/bin/env python3
"""
Initialize FileCat database
Run this script to set up the database for the first time
"""

from database import init_database

if __name__ == '__main__':
    print("Initializing FileCat database...")
    init_database()
    print("Done! You can now run the application with: python app.py")
