# Simple Bank App

A command-line bank application built in Python while learning the basics.
It lets you create accounts, deposit and withdraw money, and view
transaction history — all stored in a local SQLite database.

## Features
- Sign up: name, username, phone number, password, and a 4-digit transaction PIN
- Deposit money (opening deposit must be at least ₦500)
- Withdraw money (minimum ₦100, blocks overdrafts)
- PIN required for every deposit and withdrawal
- Check account balance
- View transaction history
- List all accounts

## Security Notes
- Passwords and PINs are **hidden while typing** (using Python's `getpass`) and must be **typed twice to confirm**.
- Passwords and PINs are never stored as plain text — they're hashed with SHA-256 before being saved. Only the hash sits in the database, so even if someone opened `bank.db` directly, they wouldn't see the real password or PIN.
- Every deposit and withdrawal asks for the account's PIN and checks it against the stored hash before the transaction goes through.

## Tech Stack
- **Python 3** (standard library only)
- **SQLite** for storage (via the built-in `sqlite3` module)

## Project Structure
```
bank-app/
├── app.py           # Command-line menu and user interaction
├── database.py      # All database setup and SQL queries
├── requirements.txt # Dependencies (none — stdlib only)
└── README.md
```

## How to Run

1. Clone the repo:
   ```bash
   git clone <your-repo-url>
   cd bank-app
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```


4. Run the app:
   ```bash
   python app.py
   ```

A file called `bank.db` will be created automatically the first time
you run the app — this is your database, and it's ignored by git.

## Example Session
```
===== SIMPLE BANK APP =====
1. Sign up (create account)
2. Deposit money
3. Withdraw money
4. Check balance
5. View transaction history
6. List all accounts
0. Exit
Choose an option: 1

--- Sign Up ---
Enter your full name: John Doe
Choose a username: john_d
Enter your phone number: 08012345678
Create a password: 
Confirm a password: 
Create a 4-digit transaction PIN: 
Confirm a 4-digit transaction PIN: 
Enter opening deposit (minimum #500): 1000

Account created! Your account ID is 1.
Remember your account ID, username, and PIN — you'll need them.
```

## Why This Project
Built as a learning project to practice:
- Python fundamentals (functions, loops, input handling)
- Working with a real database (SQLite) instead of just variables
- Structuring a small project into separate, readable files

## Possible Future Improvements
- Add a proper login step (verify username + password before showing menu)
- Add account deletion
- Add transfer money between accounts
- Lock the account after too many wrong PIN attempts
- Add unit tests
