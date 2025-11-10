import asyncio
import sqlite3
import main

async def run_test():
    # Ensure DB exists and is empty-ish
    main.init_db()

    # Clear table for a clean test
    conn = sqlite3.connect('transactions.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()

    # Call POST endpoint function directly to store SUCCESS transactions
    success_list = await main.store_and_get_success()
    print('Stored SUCCESS count (from DB):', len(success_list))

    # Verify DB has only SUCCESS rows
    conn = sqlite3.connect('transactions.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE status='SUCCESS'")
    db_success_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transactions WHERE status!='SUCCESS'")
    db_non_success_count = c.fetchone()[0]
    conn.close()
    print('DB success_count:', db_success_count)
    print('DB non_success_count:', db_non_success_count)

    # Call GET non-success endpoint function directly (should return from mockdata only)
    non_success_list = await main.get_non_success()
    print('non_success returned count (from mockdata):', len(non_success_list))

if __name__ == '__main__':
    asyncio.run(run_test())
