"""
app.py
------
A simple command-line bank application.

Run it with:
    python app.py

When the app starts, you'll see:
1. Sign up
2. Log in
0. Quit

After logging in, you get access to your account:
1. Deposit money
2. Withdraw money
3. Transfer money
4. Request loan
5. Check balance
6. View transaction history
7. Log out
0. Quit

Rules:
- Every account has a username, phone number, password, and a 4-digit
  transaction PIN, set at sign up.
- The password and PIN are entered hidden (using getpass) and must be
  confirmed by typing them twice.
- Logging in requires the correct username and password.
- For deposits, withdrawals, transfers, and loans, you enter the amount
  first — the PIN is asked right before the transaction is finalized.
- Viewing your balance and transaction history does NOT require a PIN.
- The first deposit (opening balance) must be at least #500.
- Every withdrawal must be at least #100.
- Transfers move money directly between two accounts in the database
  and are recorded in both accounts' transaction history.
- Your loan limit is the largest single deposit you've ever made. Taking
  a loan adds the amount to your balance and to a separate debt total.
  While you have debt, deposits go toward paying it off first — only
  the amount left over after clearing the debt adds to your balance.

All data is stored in a local SQLite file called bank.db (created
automatically the first time you run the app).
"""

import sqlite3
from getpass import getpass

import database as db

MIN_OPENING_DEPOSIT = 500
MIN_WITHDRAWAL = 100


# ---------- Helpers ----------

def get_confirmed_secret(prompt_label, min_length=4, digits_only=False):
    """
    Ask the user to type a secret (password or PIN) twice, hidden from
    the screen, and keep asking until both entries match and pass the
    basic rules. Returns the final secret as plain text (it gets hashed
    by the caller before it's stored).
    """
    while True:
        first = getpass(f"Create {prompt_label}: ")
        second = getpass(f"Confirm {prompt_label}: ")

        if first != second:
            print(f"{prompt_label.capitalize()}s did not match. Try again.\n")
            continue

        if digits_only and not first.isdigit():
            print(f"{prompt_label.capitalize()} must contain digits only.\n")
            continue

        if len(first) < min_length:
            print(f"{prompt_label.capitalize()} must be at least {min_length} characters.\n")
            continue

        return first


def get_non_empty_input(prompt):
    """Keep asking until the user types something other than blank/whitespace."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field can't be empty. Please try again.")


def is_valid_nigerian_phone(phone):
    """
    A Nigerian mobile number, in local format, is exactly 11 digits and
    starts with 0 (e.g. 08012345678, 07098765432, 09122334455).
    """
    return phone.isdigit() and len(phone) == 11 and phone.startswith("0")


def get_valid_phone_number():
    """Keep asking until a valid 11-digit Nigerian phone number is entered."""
    while True:
        phone_number = input("Enter your phone number (e.g. 08012345678): ").strip()
        if is_valid_nigerian_phone(phone_number):
            return phone_number
        print("That doesn't look like a valid Nigerian number.")
        print("It must be exactly 11 digits and start with 0.\n")


def get_valid_amount(prompt, minimum=0.01, minimum_message=None):
    """
    Keep asking until the user enters a valid number that meets the
    minimum. Used for every place we ask "how much?" so the rules
    are enforced the same way everywhere instead of one-off checks.
    """
    while True:
        raw_value = input(prompt).strip()
        try:
            amount = float(raw_value)
        except ValueError:
            print("Please enter a valid number.\n")
            continue

        if amount < minimum:
            print(minimum_message or f"Amount must be at least {minimum}.")
            print()
            continue

        return amount


def get_username_for_signup():
    """Keep asking for a username until one that isn't already taken is given."""
    while True:
        username = get_non_empty_input("Choose a username: ")
        if db.get_account_by_username(username):
            print("That username is already taken. Please choose another.\n")
            continue
        return username


def verify_pin(account_id):
    """Ask for the PIN and check it against the stored hash. Returns True/False."""
    entered_pin = getpass("Enter your transaction PIN: ")
    stored_hash = db.get_pin_hash(account_id)
    if stored_hash is None:
        print("Account not found.")
        return False

    if db.hash_text(entered_pin) != stored_hash:
        print("Incorrect PIN.")
        return False

    return True


# ---------- Sign up / Log in ----------

def sign_up():
    print("\n--- Sign Up ---")
    name = get_non_empty_input("Enter your full name: ")
    username = get_username_for_signup()
    phone_number = get_valid_phone_number()

    password = get_confirmed_secret("a password", min_length=4)
    pin = get_confirmed_secret("a 4-digit transaction PIN", min_length=4, digits_only=True)

    opening_balance = get_valid_amount(
        f"Enter opening deposit (minimum #{MIN_OPENING_DEPOSIT}): ",
        minimum=MIN_OPENING_DEPOSIT,
        minimum_message=f"Opening deposit must be at least #{MIN_OPENING_DEPOSIT}."
    )

    password_hash = db.hash_text(password)
    pin_hash = db.hash_text(pin)

    try:
        account_id = db.create_account(name, username, phone_number, password_hash, pin_hash, opening_balance)
    except sqlite3.IntegrityError:
        print("That username is already taken. Please try signing up again.")
        return

    db.add_transaction(account_id, "deposit", opening_balance)
    account = db.get_account(account_id)
    account_number = account[6]

    print(f"\nAccount created successfully!")
    print(f"Your account number is {account_number}")
    print("You can now log in with your username and password.")


def log_in():
    print("\n--- Log In ---")
    username = input("Username: ").strip()
    password = getpass("Password: ")

    account = db.get_account_by_username(username)
    if not account:
        print("Invalid username or password.")
        return None

    account_id, name, username, phone_number, password_hash, balance = account

    if db.hash_text(password) != password_hash:
        print("Invalid username or password.")
        return None

    print(f"\nWelcome back, {name}!")
    return account_id


# ---------- Banking actions (require an active session) ----------

def deposit_money(account_id):
    amount = get_valid_amount("Enter the amount you want to deposit: ", minimum=0.01)

    if not verify_pin(account_id):
        return

    account = db.get_account(account_id)
    debt = account[5]

    if debt > 0:
        # The deposit goes toward the loan first. Only the amount left
        # over after clearing debt (if any) actually adds to the balance.
        repayment = min(amount, debt)
        leftover = amount - repayment
        new_debt = debt - repayment
        new_balance = account[4] + leftover

        db.update_balance(account_id, new_balance)
        db.update_debt(account_id, new_debt)
        db.add_transaction(account_id, "deposit", amount)

        print(f"Deposited {amount:.2f}. #{repayment:.2f} went toward your loan.")
        if leftover > 0:
            print(f"#{leftover:.2f} was added to your balance.")
        print(f"Balance: {new_balance:.2f} | Remaining debt: {new_debt:.2f}")
    else:
        new_balance = account[4] + amount
        db.update_balance(account_id, new_balance)
        db.add_transaction(account_id, "deposit", amount)
        print(f"Deposited {amount:.2f}. New balance: {new_balance:.2f}")


def withdraw_money(account_id):
    amount = get_valid_amount(
        "Enter the amount you'd like to withdraw: ",
        minimum=MIN_WITHDRAWAL,
        minimum_message=f"Minimum withdrawal is #{MIN_WITHDRAWAL}."
    )

    account = db.get_account(account_id)
    if amount > account[4]:
        print("Insufficient funds.")
        return

    if not verify_pin(account_id):
        return

    new_balance = account[4] - amount
    db.update_balance(account_id, new_balance)
    db.add_transaction(account_id, "withdraw", amount)
    print(f"Withdrew {amount:.2f}. New balance: {new_balance:.2f}")


def transfer_money(account_id):
    recipient_username = get_non_empty_input("Enter the recipient's username: ")
    recipient = db.get_account_by_username(recipient_username)

    if not recipient:
        print("Recipient not found.")
        return

    recipient_id = recipient[0]
    if recipient_id == account_id:
        print("You can't transfer money to yourself.")
        return

    amount = get_valid_amount("Enter the amount you want to transfer: ", minimum=0.01)

    sender = db.get_account(account_id)
    if amount > sender[4]:
        print("Insufficient funds.")
        return

    if not verify_pin(account_id):
        return

    # Move the money.
    sender_new_balance = sender[4] - amount
    recipient_new_balance = recipient[5] + amount
    db.update_balance(account_id, sender_new_balance)
    db.update_balance(recipient_id, recipient_new_balance)

    # Record it on both sides so each person's history makes sense.
    db.add_transaction(account_id, "transfer_out", amount)
    db.add_transaction(recipient_id, "transfer_in", amount)

    print(f"Transferred {amount:.2f} to {recipient[1]} (@{recipient_username}).")
    print(f"New balance: {sender_new_balance:.2f}")


def request_loan(account_id):
    max_loan = db.get_max_deposit(account_id)
    if max_loan <= 0:
        print("You need to have made at least one deposit before you can request a loan.")
        return

    print(f"Your maximum loan amount is #{max_loan:.2f} (your biggest deposit so far).")
    amount = get_valid_amount(
        "Enter the amount you'd like to borrow: ",
        minimum=0.01,
        minimum_message=f"You can't borrow more than #{max_loan:.2f}. Enter an amount greater than 0."
    )

    if amount > max_loan:
        print(f"You can't borrow more than #{max_loan:.2f}. Please try a smaller amount.")
        return

    if not verify_pin(account_id):
        return

    account = db.get_account(account_id)
    new_balance = account[4] + amount
    new_debt = account[5] + amount
    db.update_balance(account_id, new_balance)
    db.update_debt(account_id, new_debt)
    db.add_transaction(account_id, "loan", amount)

    print(f"Loan of {amount:.2f} approved and added to your balance.")
    print(f"New balance: {new_balance:.2f} | Outstanding debt: {new_debt:.2f}")
    print("This debt will be automatically reduced whenever you make a deposit.")


def check_balance(account_id):
    account = db.get_account(account_id)
    print(f"Account {account[6]} ({account[1]}) balance: {account[4]:.2f}")
    if account[5] > 0:
        print(f"Outstanding loan debt: {account[5]:.2f}")


def view_transactions(account_id):
    account = db.get_account(account_id)
    transactions = db.get_transactions(account_id)
    if not transactions:
        print("No transactions yet.")
        return

    print(f"\nTransaction history for {account[1]}:")
    for t_type, amount, timestamp in transactions:
        print(f"  [{timestamp}] {t_type:<12} {amount:.2f}")


# ---------- Menus ----------

def session_menu(account_id):
    """Shown after a successful login. Returns when the user logs out or quits."""
    while True:
        print("\n----- YOUR ACCOUNT -----")
        print("1. Deposit money")
        print("2. Withdraw money")
        print("3. Transfer money")
        print("4. Request loan")
        print("5. Check balance")
        print("6. View transaction history")
        print("7. Log out")
        print("0. Quit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            deposit_money(account_id)
        elif choice == "2":
            withdraw_money(account_id)
        elif choice == "3":
            transfer_money(account_id)
        elif choice == "4":
            request_loan(account_id)
        elif choice == "5":
            check_balance(account_id)
        elif choice == "6":
            view_transactions(account_id)
        elif choice == "7":
            print("Logged out.")
            return "logout"
        elif choice == "0":
            print("Goodbye!")
            return "quit"
        else:
            print("Invalid option, try again.")


def main():
    db.init_db()

    while True:
        print("\n===== SIMPLE BANK APP =====")
        print("1. Sign up")
        print("2. Log in")
        print("0. Quit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            sign_up()
        elif choice == "2":
            account_id = log_in()
            if account_id is not None:
                result = session_menu(account_id)
                if result == "quit":
                    break
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    main()
