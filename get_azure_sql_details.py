#!/usr/bin/env python3
"""
Helper script to show you what environment variables to set in Azure App Service
"""

def show_environment_variables_guide():
    print("=" * 60)
    print("AZURE SQL DATABASE ENVIRONMENT VARIABLES GUIDE")
    print("=" * 60)
    print()
    
    print("1. Go to Azure Portal → SQL databases → rhythmic → Connection strings")
    print("2. Copy the ADO.NET connection string")
    print("3. Extract these values from the connection string:")
    print()
    
    print("Example connection string:")
    print("Server=tcp:my-server.database.windows.net,1433;Initial Catalog=rhythmic;User ID=my_admin;Password=MyPass123;...")
    print()
    
    print("Extract these parts:")
    print("┌─────────────────────┬──────────────────────────────────────────┐")
    print("│ Environment Variable │ Value from Connection String             │")
    print("├─────────────────────┼──────────────────────────────────────────┤")
    print("│ AZURE_SQL_SERVER    │ my-server.database.windows.net           │")
    print("│ AZURE_SQL_USER      │ my_admin                                 │")
    print("│ AZURE_SQL_PASSWORD  │ MyPass123                                │")
    print("│ AZURE_SQL_DATABASE  │ rhythmic                                 │")
    print("└─────────────────────┴──────────────────────────────────────────┘")
    print()
    
    print("4. In Azure App Service → Configuration → Application settings:")
    print("   Click '+ New application setting' for each variable above")
    print()
    
    print("5. Your final environment variables should look like:")
    print()
    
    # Get user input for their actual values
    print("Enter your actual values (or press Enter to skip):")
    server = input("Server name (without tcp: and ,1433): ").strip()
    user = input("Admin username: ").strip()
    password = input("Admin password: ").strip()
    database = input("Database name [rhythmic]: ").strip() or "rhythmic"
    
    if server and user and password:
        print()
        print("=" * 60)
        print("YOUR ENVIRONMENT VARIABLES:")
        print("=" * 60)
        print(f"AZURE_SQL_SERVER    = {server}")
        print(f"AZURE_SQL_USER      = {user}")
        print(f"AZURE_SQL_PASSWORD  = {password}")
        print(f"AZURE_SQL_DATABASE  = {database}")
        print()
        print("Copy these exact values into Azure App Service Configuration!")
        print()
        
        # Show the complete connection string
        connection_string = f"mssql+pyodbc://{user}:{password}@{server}:1433/{database}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
        print("Complete connection string (for reference):")
        print(connection_string)
    
    print()
    print("=" * 60)
    print("TROUBLESHOOTING:")
    print("=" * 60)
    print("• Make sure server name ends with '.database.windows.net'")
    print("• Don't include 'tcp:' or ',1433' in the server name")
    print("• Use the exact username and password from when you created the database")
    print("• Database name should be 'rhythmic' (or whatever you named it)")
    print("• Click 'Save' in Azure App Service after adding all variables")

if __name__ == "__main__":
    show_environment_variables_guide()