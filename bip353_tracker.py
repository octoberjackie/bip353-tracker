import os
import re
import time
import json
import logging
import requests
from datetime import datetime
from github import Github, RateLimitExceededException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bip353_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bip353-tracker")

# Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is not set")

# List of repositories to check
REPOSITORIES = [
    "breez/breezmobile",
    "satochip/wallet",
    "LightningLabs/lightning-app",
    "btcpayserver/btcpayserver",
    "ElectrumWallet/Electrum",
    "BlueWallet/BlueWallet",
    "LightningTipBot/LightningTipBot",
    "phoenix-wallet/phoenix",
    "muun/apollo",
    # Add more repositories as needed
]

# Initialize GitHub client
github_client = Github(GITHUB_TOKEN)

def check_bip353_support(repo_name):
    """
    Check if a repository supports BIP-353, has implementation in progress,
    or doesn't support it yet.
    
    Returns: 
        dict: Repository information including support status
    """
    try:
        logger.info(f"Checking repository: {repo_name}")
        repo = github_client.get_repo(repo_name)
        
        # Get default branch
        default_branch = repo.default_branch
        
        # Initialize result
        result = {
            "name": repo.name,
            "full_name": repo.full_name,
            "url": repo.html_url,
            "stars": repo.stargazers_count,
            "last_updated": repo.updated_at.isoformat(),
            "bip353_status": "Not Supported",
            "evidence": []
        }
        
        # Check README and documentation
        try:
            readme_content = repo.get_readme().decoded_content.decode('utf-8')
            if re.search(r'BIP-?353', readme_content, re.IGNORECASE):
                result["evidence"].append("BIP-353 mentioned in README")
        except Exception as e:
            logger.warning(f"Couldn't fetch README for {repo_name}: {e}")
        
        # Search for BIP-353 in code
        try:
            code_results = repo.get_contents("")
            code_files = []
            
            # Recursive function to search through all files
            def search_directory(contents):
                nonlocal code_files
                for content in contents:
                    if content.type == "dir":
                        try:
                            search_directory(repo.get_contents(content.path))
                        except Exception as e:
                            logger.warning(f"Couldn't access directory {content.path}: {e}")
                    elif content.type == "file" and content.name.endswith(('.py', '.js', '.ts', '.go', '.c', '.cpp', '.h', '.rs', '.java')):
                        try:
                            file_content = content.decoded_content.decode('utf-8')
                            if re.search(r'BIP-?353', file_content, re.IGNORECASE):
                                code_files.append(content.path)
                        except Exception as e:
                            logger.warning(f"Couldn't read file {content.path}: {e}")
            
            # Only search first level directories to avoid excessive API calls
            for content in code_results:
                if content.type == "dir" and content.name in ["src", "lib", "core", "docs", "test", "tests"]:
                    try:
                        search_directory(repo.get_contents(content.path))
                    except Exception as e:
                        logger.warning(f"Couldn't access directory {content.path}: {e}")
            
            if code_files:
                result["evidence"].append(f"BIP-353 mentioned in code files: {', '.join(code_files)}")
        except Exception as e:
            logger.warning(f"Couldn't search code for {repo_name}: {e}")
        
        # Search for issues and PRs related to BIP-353
        open_issues = list(repo.get_issues(state="open", labels=None))
        closed_issues = list(repo.get_issues(state="closed", labels=None))
        
        bip353_open_issues = [issue for issue in open_issues if re.search(r'BIP-?353', issue.title + (issue.body or ""), re.IGNORECASE)]
        bip353_closed_issues = [issue for issue in closed_issues if re.search(r'BIP-?353', issue.title + (issue.body or ""), re.IGNORECASE)]
        
        if bip353_open_issues:
            result["evidence"].append(f"Found {len(bip353_open_issues)} open issues/PRs related to BIP-353")
        
        if bip353_closed_issues:
            result["evidence"].append(f"Found {len(bip353_closed_issues)} closed issues/PRs related to BIP-353")
        
        # Determine BIP-353 support status based on evidence
        if result["evidence"]:
            # Check if there are implementation files
            implementation_files = [file for file in code_files if re.search(r'(implement|support).*BIP-?353', file, re.IGNORECASE)]
            
            if implementation_files or any("implemented" in issue.title.lower() for issue in bip353_closed_issues):
                result["bip353_status"] = "Supported"
            else:
                result["bip353_status"] = "In Progress"
        
        logger.info(f"Completed check for {repo_name}: {result['bip353_status']}")
        return result
    
    except RateLimitExceededException:
        logger.error("GitHub API rate limit exceeded. Waiting before retrying.")
        # Handle rate limiting by sleeping
        rate_limit = github_client.get_rate_limit()
        reset_timestamp = rate_limit.core.reset.timestamp()
        sleep_time = reset_timestamp - time.time() + 60  # Add 60 seconds buffer
        if sleep_time > 0:
            logger.info(f"Sleeping for {sleep_time} seconds due to rate limiting")
            time.sleep(sleep_time)
        return check_bip353_support(repo_name)  # Retry after waiting
    
    except Exception as e:
        logger.error(f"Error checking {repo_name}: {str(e)}")
        return {
            "name": repo_name.split('/')[-1],
            "full_name": repo_name,
            "url": f"https://github.com/{repo_name}",
            "stars": 0,
            "last_updated": datetime.now().isoformat(),
            "bip353_status": "Error",
            "evidence": [f"Error checking repository: {str(e)}"]
        }

def generate_markdown_table(results):
    """
    Generate a markdown table from repository check results
    """
    # Sort results by status and then by name
    status_order = {"Supported": 0, "In Progress": 1, "Not Supported": 2, "Error": 3}
    sorted_results = sorted(results, key=lambda x: (status_order.get(x["bip353_status"], 4), x["name"]))
    
    markdown = "# BIP-353 Support in Bitcoin/Lightning Projects\n\n"
    markdown += f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n\n"
    
    markdown += "| Project | BIP-353 Status | Stars | Evidence |\n"
    markdown += "|---------|---------------|-------|----------|\n"
    
    for repo in sorted_results:
        name_with_link = f"[{repo['name']}]({repo['url']})"
        status = repo["bip353_status"]
        stars = repo["stars"]
        evidence = "<br>".join(repo["evidence"]) if repo["evidence"] else "None found"
        
        markdown += f"| {name_with_link} | {status} | {stars} | {evidence} |\n"
    
    # Add summary statistics
    supported = sum(1 for repo in results if repo["bip353_status"] == "Supported")
    in_progress = sum(1 for repo in results if repo["bip353_status"] == "In Progress")
    not_supported = sum(1 for repo in results if repo["bip353_status"] == "Not Supported")
    
    markdown += f"\n## Summary\n\n"
    markdown += f"- Supported: {supported}\n"
    markdown += f"- In Progress: {in_progress}\n"
    markdown += f"- Not Supported: {not_supported}\n"
    
    return markdown

def save_results(results, markdown):
    """
    Save results to JSON and markdown files
    """
    # Save JSON data
    with open("bip353_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save markdown table
    with open("BIP353_SUPPORT.md", "w") as f:
        f.write(markdown)
    
    logger.info("Results saved to bip353_results.json and BIP353_SUPPORT.md")

def main():
    """
    Main function to check repositories and generate report
    """
    logger.info("Starting BIP-353 support check")
    
    results = []
    for repo_name in REPOSITORIES:
        try:
            result = check_bip353_support(repo_name)
            results.append(result)
            # Avoid hitting rate limits
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to process {repo_name}: {e}")
    
    markdown = generate_markdown_table(results)
    save_results(results, markdown)
    
    logger.info("Completed BIP-353 support check")

if __name__ == "__main__":
    main()
