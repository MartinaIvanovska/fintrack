// MongoDB initialization script
// Creates indexes for optimal query performance

db = db.getSiblingDB('finance_tracker');

// Users indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ username: 1 }, { unique: true });

// Transactions indexes
db.transactions.createIndex({ user_id: 1, date: -1 });
db.transactions.createIndex({ user_id: 1, type: 1 });
db.transactions.createIndex({ user_id: 1, category_id: 1 });
db.transactions.createIndex({ description: "text", merchant: "text" });

// Categories indexes
db.categories.createIndex({ user_id: 1, type: 1 });

// Budgets indexes
db.budgets.createIndex({ user_id: 1, month_year: 1 });
db.budgets.createIndex({ user_id: 1, category_id: 1, month_year: 1 }, { unique: true });

print("Finance Tracker DB initialized with indexes.");
