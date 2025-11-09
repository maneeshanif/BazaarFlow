#!/usr/bin/env python
"""
Diagnostic script to troubleshoot Facebook Manager CLI issues.

Run this to check your configuration and identify common problems.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_status(message: str, status: str):
    """Print a status message with color coding."""
    if status == "OK":
        print(f"{GREEN}✓{RESET} {message}")
    elif status == "WARNING":
        print(f"{YELLOW}⚠{RESET} {message}")
    elif status == "ERROR":
        print(f"{RED}✗{RESET} {message}")
    else:
        print(f"{BLUE}ℹ{RESET} {message}")


def check_env_file():
    """Check if .env file exists and is readable."""
    env_path = Path(".env")
    if not env_path.exists():
        print_status(".env file not found", "ERROR")
        print(f"  → Create a .env file in {Path.cwd()}")
        return False
    
    print_status(f".env file found at {env_path.absolute()}", "OK")
    
    # Check if readable
    try:
        env_path.read_text()
        print_status(".env file is readable", "OK")
        return True
    except Exception as e:
        print_status(f".env file cannot be read: {e}", "ERROR")
        return False


def check_environment_variables():
    """Check if required environment variables are set."""
    load_dotenv()
    
    required = {
        "FACEBOOK_PAGE_ID": "Your Facebook Page ID (numeric)",
        "FACEBOOK_ACCESS_TOKEN": "Your Facebook Page Access Token"
    }
    
    all_ok = True
    for var, description in required.items():
        value = os.getenv(var)
        
        if not value:
            print_status(f"{var} not set", "ERROR")
            print(f"  → {description}")
            all_ok = False
            continue
        
        # Check format
        if var == "FACEBOOK_PAGE_ID":
            if not value.isdigit():
                print_status(f"{var} format invalid (should be numeric)", "WARNING")
                print(f"  → Current value: {value}")
            else:
                print_status(f"{var} is set and looks valid", "OK")
        
        elif var == "FACEBOOK_ACCESS_TOKEN":
            if len(value) < 50:
                print_status(f"{var} seems too short", "WARNING")
                print(f"  → Token length: {len(value)} characters (expected 100+)")
            else:
                # Check if token starts with expected prefix
                if value.startswith("EAA"):
                    print_status(f"{var} is set and format looks correct", "OK")
                else:
                    print_status(f"{var} format might be incorrect", "WARNING")
                    print(f"  → Expected to start with 'EAA', starts with: {value[:10]}...")
    
    return all_ok


def check_token_expiration():
    """Attempt to verify token with Facebook API."""
    try:
        from src import FacebookManager
        
        print_status("Attempting to verify credentials with Facebook...", "INFO")
        
        try:
            with FacebookManager() as manager:
                result = manager.verify_credentials()
                
                if result:
                    print_status("Facebook credentials verified successfully!", "OK")
                    return True
                else:
                    print_status("Credentials verification returned False", "WARNING")
                    return False
        
        except Exception as e:
            error_str = str(e).lower()
            
            if "expired" in error_str or "session" in error_str:
                print_status("Facebook access token has EXPIRED", "ERROR")
                print(f"  → Error: {e}")
                print(f"  → Generate a new token at: https://developers.facebook.com/tools/explorer/")
                return False
            
            elif "invalid" in error_str or "190" in error_str:
                print_status("Facebook credentials are INVALID", "ERROR")
                print(f"  → Error: {e}")
                return False
            
            else:
                print_status(f"Failed to verify credentials: {e}", "ERROR")
                return False
    
    except ImportError:
        print_status("Cannot import FacebookManager (is src/ package available?)", "ERROR")
        return False


def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        "pydantic",
        "pydantic_settings",
        "requests",
        "dotenv",
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print_status(f"Package '{package}' is installed", "OK")
        except ImportError:
            print_status(f"Package '{package}' is NOT installed", "ERROR")
            all_ok = False
    
    if not all_ok:
        print("\n  → Install missing packages with: pip install -r requirements.txt")
    
    return all_ok


def check_main_script():
    """Check if main.py exists and is executable."""
    main_path = Path("main.py")
    
    if not main_path.exists():
        print_status("main.py not found", "ERROR")
        return False
    
    print_status("main.py found", "OK")
    
    # Try to import and check structure
    try:
        import main
        print_status("main.py imports successfully", "OK")
        
        # Check if main function exists
        if hasattr(main, "main"):
            print_status("main() function exists", "OK")
        else:
            print_status("main() function not found", "WARNING")
        
        return True
    
    except Exception as e:
        print_status(f"Cannot import main.py: {e}", "ERROR")
        return False


def provide_recommendations(results):
    """Provide recommendations based on diagnostic results."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}RECOMMENDATIONS{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    if not results["env_file"]:
        print("1. Create a .env file in the project root with:")
        print("   FACEBOOK_PAGE_ID=your_page_id")
        print("   FACEBOOK_ACCESS_TOKEN=your_token\n")
    
    if not results["env_vars"]:
        print("2. Ensure your .env file contains valid values:")
        print("   - Page ID should be numeric only")
        print("   - Access token should be 100+ characters\n")
    
    if not results["token"]:
        print("3. Your access token may be expired or invalid:")
        print(f"   → Visit: {YELLOW}https://developers.facebook.com/tools/explorer/{RESET}")
        print("   → Select your app and page")
        print("   → Request permissions: pages_manage_posts, pages_read_engagement")
        print("   → Generate a new Page Access Token")
        print("   → Copy the token to your .env file\n")
    
    if not results["dependencies"]:
        print("4. Install missing dependencies:")
        print("   pip install -r requirements.txt\n")
    
    if all(results.values()):
        print(f"{GREEN}✓ All checks passed! Your setup looks good.{RESET}")
        print("\nYou can now use commands like:")
        print("  python main.py verify")
        print("  python main.py post-text 'Hello, World!'")
        print("  python main.py fetch-post-engagement YOUR_POST_ID")


def main():
    """Run all diagnostic checks."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Facebook Manager CLI Diagnostics{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    print(f"Current directory: {Path.cwd()}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    print(f"{BLUE}Checking environment file...{RESET}")
    results["env_file"] = check_env_file()
    print()
    
    print(f"{BLUE}Checking environment variables...{RESET}")
    results["env_vars"] = check_environment_variables()
    print()
    
    print(f"{BLUE}Checking Python dependencies...{RESET}")
    results["dependencies"] = check_dependencies()
    print()
    
    print(f"{BLUE}Checking main.py script...{RESET}")
    results["main_script"] = check_main_script()
    print()
    
    print(f"{BLUE}Verifying Facebook API credentials...{RESET}")
    results["token"] = check_token_expiration()
    print()
    
    provide_recommendations(results)
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Diagnostics cancelled by user.{RESET}")
        sys.exit(130)
