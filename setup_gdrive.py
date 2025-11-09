"""
Setup script for Google Drive MCP Server authentication
This script helps you authenticate with Google Drive and verify the setup.
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def check_nodejs() -> bool:
    """Check if Node.js and npx are installed."""
    print_header("Checking Node.js Installation")
    npx_path = shutil.which("npx")
    try:
        node_result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        if not npx_path:
            raise FileNotFoundError
        npx_result = subprocess.run(
            [npx_path, "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Node.js is installed: {node_result.stdout.strip()}")
        print(f"✓ npx is available: {npx_result.stdout.strip()} ({npx_path})")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Node.js or npx is not installed or not in PATH")
        print("\nInstall the latest LTS version from https://nodejs.org/ and reopen this terminal.")
        return False


def locate_npx() -> str:
    """Return the absolute path to npx or raise a helpful error."""
    npx_path = shutil.which("npx")
    if npx_path:
        return npx_path

    # On some systems npx may be npx.cmd or located next to npm
    fallback_candidates = [
        shutil.which("npx.cmd"),
        shutil.which("npm"),
        shutil.which("npm.cmd"),
    ]
    for candidate in fallback_candidates:
        if candidate:
            # For npm, npx usually lives in the same directory
            if candidate.lower().endswith("npm") or candidate.lower().endswith("npm.cmd"):
                possible = Path(candidate).with_name("npx.cmd")
                if possible.exists():
                    return str(possible)
            else:
                return candidate

    raise FileNotFoundError(
        "Could not locate 'npx'. Install Node.js from https://nodejs.org/ and make sure you start "
        "a new terminal so that npm's bin directory is added to PATH."
    )


def check_oauth_keys():
    """Check if OAuth keys file exists."""
    print_header("Checking OAuth Keys")
    oauth_path = Path("gcp-oauth.keys.json")
    
    if oauth_path.exists():
        print(f"✓ OAuth keys file found: {oauth_path}")
        
        # Validate JSON
        try:
            with open(oauth_path) as f:
                data = json.load(f)
                if "installed" in data or "web" in data:
                    print("✓ OAuth keys file appears valid")
                    return True
                else:
                    print("⚠ Warning: OAuth keys file may not be in the correct format")
                    return False
        except json.JSONDecodeError:
            print("✗ OAuth keys file is not valid JSON")
            return False
    else:
        print(f"✗ OAuth keys file not found: {oauth_path}")
        print("\nPlease follow these steps:")
        print("1. Go to: https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop App)")
        print("3. Download the JSON file")
        print("4. Rename it to 'gcp-oauth.keys.json'")
        print("5. Place it in the project root directory")
        return False


def check_credentials():
    """Check if credentials file exists."""
    print_header("Checking Credentials")
    creds_path = Path(".gdrive-server-credentials.json")
    
    if creds_path.exists():
        print(f"✓ Credentials file found: {creds_path}")
        print("  You are already authenticated!")
        return True
    else:
        print(f"✗ Credentials file not found: {creds_path}")
        print("  You need to authenticate first")
        return False


def run_authentication():
    """Run the authentication flow."""
    print_header("Running Authentication Flow")
    print("This will open a browser window for you to authenticate...")
    print("After authentication, credentials will be saved automatically.\n")
    
    env = os.environ.copy()
    env["GDRIVE_OAUTH_PATH"] = "gcp-oauth.keys.json"
    env["GDRIVE_CREDENTIALS_PATH"] = ".gdrive-server-credentials.json"
    env["GDRIVE_SCOPES"] = ",".join([
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
    ])
    
    try:
        print("Starting MCP server for authentication...\n")
        # Run the server - it should handle the auth flow
        npx_path = locate_npx()
        subprocess.run(
            [npx_path, "-y", "@modelcontextprotocol/server-gdrive"],
            env=env,
            check=True
        )
        print("\n✓ Authentication completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Authentication failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n✗ Authentication cancelled by user")
        return False


def verify_setup():
    """Verify the complete setup."""
    print_header("Verifying Complete Setup")
    
    checks = {
        "Node.js installed": check_nodejs(),
        "OAuth keys present": check_oauth_keys(),
        "Credentials present": check_credentials(),
    }
    
    print("\nSetup Status:")
    print("-" * 40)
    for check, status in checks.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {check}")
    print("-" * 40)
    
    all_good = all(checks.values())
    
    if all_good:
        print("\n✓ All checks passed! You're ready to use the agent.")
        print("\nNext steps:")
        print("1. Install Python dependencies: pip install -e .")
        print("2. Run the example: python example_usage.py")
    else:
        print("\n✗ Some checks failed. Please address the issues above.")
    
    return all_good


def main():
    """Main setup function."""
    print_header("Google Drive MCP Server Setup")
    
    # First verify Node.js
    if not check_nodejs():
        sys.exit(1)
    
    # Check OAuth keys
    if not check_oauth_keys():
        print("\n⚠ Cannot proceed without OAuth keys.")
        sys.exit(1)
    
    # Check if already authenticated
    if check_credentials():
        print("\n✓ Already authenticated!")
        choice = input("\nDo you want to re-authenticate? (y/N): ").strip().lower()
        if choice != 'y':
            print("\nSkipping authentication.")
            verify_setup()
            return
    
    # Run authentication
    print("\nStarting authentication process...")
    choice = input("Continue? (Y/n): ").strip().lower()
    
    if choice == 'n':
        print("Setup cancelled.")
        sys.exit(0)
    
    if run_authentication():
        verify_setup()
    else:
        print("\n✗ Setup incomplete. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
