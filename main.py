# My-Super-Agent v1.0 - GitHub Automation System
# Complete GitHub repository management system with CLI and agent capabilities

import os
import sys
import argparse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import tool, initialize_agent, AgentType
from services.github_ops import (
    get_user_info, list_repositories, create_repository, 
    create_or_update_file, sync_project_to_repo, create_repo_and_sync,
    GitHubError
)
from services.web_tools import (
    test_website_liveness, extract_page_content, monitor_website_changes,
    WebPerceptionError
)

# LangChain Tools for GitHub Operations
@tool
def list_my_github_repos(query: str) -> str:
    """
    List all GitHub repositories for the authenticated user.
    Input: any text (will be ignored)
    """
    try:
        user = get_user_info()
        repos = list_repositories()
        repo_names = [repo['name'] for repo in repos]
        
        if not repo_names:
            return f"Connected as '{user['login']}' but found 0 repositories."
        
        return f"SUCCESS! Connected as '{user['login']}'. Found {len(repo_names)} repositories: {', '.join(repo_names)}"
    except GitHubError as e:
        return f"GitHub Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@tool
def create_github_repo(repo_info: str) -> str:
    """
    Create a new GitHub repository.
    Input should be in format: "name|description|private(true/false)|org(optional)"
    Example: "my-project|A sample project|true|"
    """
    try:
        parts = repo_info.split('|')
        if len(parts) < 3:
            return "Error: Invalid format. Use: name|description|private(true/false)|org(optional)"
        
        name = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        private = parts[2].strip().lower() == 'true' if len(parts) > 2 else True
        org = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
        
        repo = create_repository(name, description, private, org)
        return f"SUCCESS! Repository '{name}' created: {repo['html_url']}"
        
    except GitHubError as e:
        return f"GitHub Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@tool
def sync_project_to_github(repo_info: str) -> str:
    """
    Sync current project files to an existing GitHub repository.
    Input format: "owner/repo_name|branch(optional)"
    Example: "username/my-repo|main"
    """
    try:
        parts = repo_info.split('|')
        if len(parts) < 1:
            return "Error: Invalid format. Use: owner/repo_name|branch(optional)"
        
        repo_path = parts[0].strip().split('/')
        if len(repo_path) != 2:
            return "Error: Repository format should be owner/repo_name"
        
        owner, repo = repo_path
        branch = parts[1].strip() if len(parts) > 1 and parts[1].strip() else 'main'
        
        synced_files = sync_project_to_repo(owner, repo, '.', branch)
        return f"SUCCESS! Synced {len(synced_files)} files to {owner}/{repo} on branch {branch}"
        
    except GitHubError as e:
        return f"GitHub Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@tool
def create_repo_and_upload_project(repo_info: str) -> str:
    """
    Create a new repository and upload the current project files to it.
    Input format: "name|description|private(true/false)|org(optional)"
    Example: "my-project|A sample project|true|"
    """
    try:
        parts = repo_info.split('|')
        if len(parts) < 3:
            return "Error: Invalid format. Use: name|description|private(true/false)|org(optional)"
        
        name = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        private = parts[2].strip().lower() == 'true' if len(parts) > 2 else True
        org = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
        
        result = create_repo_and_sync(name, description, private, '.', org)
        if result:
            return f"SUCCESS! Created repository and synced {len(result['synced_files'])} files: {result['url']}"
        else:
            return "Failed to create repository and sync files"
        
    except GitHubError as e:
        return f"GitHub Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

# LangChain Tools for Web Perception
@tool
def test_website_liveness_tool(url: str) -> str:
    """
    Test if a website is accessible and check for errors.
    Input: URL to test (e.g., "https://example.com")
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        result = test_website_liveness(url, check_errors=True, timeout=30)
        
        status = "✓ ACCESSIBLE" if result['accessible'] else "✗ NOT ACCESSIBLE"
        response = f"Website: {url}\nStatus: {status}\n"
        response += f"Title: {result['title']}\n"
        response += f"Load Time: {result['load_time']}s\n"
        response += f"Page Size: {result['page_size']} characters\n"
        
        if result['errors']:
            response += f"\n🚨 ERRORS FOUND ({len(result['errors'])}):\n"
            for error in result['errors']:
                response += f"  • {error}\n"
        
        if result['warnings']:
            response += f"\n⚠️ WARNINGS ({len(result['warnings'])}):\n"
            for warning in result['warnings']:
                response += f"  • {warning}\n"
        
        if result['screenshot_taken']:
            response += f"\n📸 Screenshot saved: {result.get('screenshot_path', 'N/A')}"
        
        if not result['errors'] and not result['warnings']:
            response += "\n✅ No issues detected!"
        
        return response
        
    except WebPerceptionError as e:
        return f"Web Perception Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

@tool
def extract_page_content_tool(content_request: str) -> str:
    """
    Extract specific content from a webpage.
    Input format: "url|content_type" where content_type can be: text, links, images, forms
    Example: "https://example.com|text" or "https://news.com|links"
    """
    try:
        parts = content_request.split('|')
        if len(parts) != 2:
            return "Error: Invalid format. Use: url|content_type (text/links/images/forms)"
        
        url, content_type = parts[0].strip(), parts[1].strip().lower()
        
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        if content_type not in ['text', 'links', 'images', 'forms']:
            return "Error: content_type must be one of: text, links, images, forms"
        
        result = extract_page_content(url, content_type, timeout=30)
        
        if not result['success']:
            return f"Failed to extract content from {url}: {result['error']}"
        
        response = f"Content extracted from: {url}\nType: {content_type}\n\n"
        
        if content_type == 'text':
            text_content = result['content'][:2000]  # Limit to first 2000 chars
            if len(result['content']) > 2000:
                text_content += "\n... (truncated)"
            response += text_content
            
        elif content_type == 'links':
            links = result['content'][:20]  # First 20 links
            response += f"Found {len(result['content'])} links (showing first {len(links)}):\n"
            for link in links:
                response += f"• {link['text'][:50]} → {link['href']}\n"
                
        elif content_type == 'images':
            images = result['content'][:15]  # First 15 images
            response += f"Found {len(result['content'])} images (showing first {len(images)}):\n"
            for img in images:
                response += f"• {img['alt']} → {img['src']}\n"
                
        elif content_type == 'forms':
            forms = result['content']
            response += f"Found {len(forms)} forms:\n"
            for i, form in enumerate(forms):
                response += f"Form {i+1}: {form['action']} ({form['method']})\n"
                for inp in form['inputs'][:5]:  # First 5 inputs per form
                    response += f"  - {inp['type']}: {inp['name']}\n"
        
        return response
        
    except WebPerceptionError as e:
        return f"Web Perception Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

def initialize_agent_system():
    """Initialize the LangChain agent with GitHub and Web Perception tools."""
    print("Initializing Super-Agent with GitHub and Web tools...")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        tools = [
            # GitHub Operations
            list_my_github_repos,
            create_github_repo,
            sync_project_to_github,
            create_repo_and_upload_project,
            # Web Perception Tools
            test_website_liveness_tool,
            extract_page_content_tool
        ]
        agent = initialize_agent(
            tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
            verbose=True, handle_parsing_errors=True
        )
        print("✓ Super-Agent initialized with GitHub and Web Perception tools")
        return agent
    except Exception as e:
        print(f"✗ Error initializing agent: {e}")
        return None

def run_agent_task(agent, task: str):
    """Run a task using the agent."""
    if agent and task:
        print(f"\n--- Running Task: '{task}' ---")
        try:
            response = agent.run(task)
            print("\n--- Agent Response ---")
            print(response)
            print("--- Task Completed ---\n")
        except Exception as e:
            print(f"✗ Error running task: {e}")

# CLI Commands
def cmd_list_repos(args):
    """CLI command to list repositories."""
    try:
        user = get_user_info()
        repos = list_repositories()
        print(f"\n✓ Connected as: {user['login']}")
        print(f"✓ Found {len(repos)} repositories:")
        for repo in repos:
            visibility = "🔒 Private" if repo['private'] else "🌍 Public"
            print(f"  • {repo['name']} - {visibility}")
            if repo.get('description'):
                print(f"    {repo['description']}")
        print()
    except GitHubError as e:
        print(f"✗ Error: {e}")

def cmd_create_repo(args):
    """CLI command to create a repository."""
    try:
        repo = create_repository(args.name, args.description, args.private, args.org)
        print(f"✓ Repository created: {repo['html_url']}")
    except GitHubError as e:
        print(f"✗ Error: {e}")

def cmd_sync_project(args):
    """CLI command to sync project to repository."""
    try:
        owner, repo = args.repository.split('/')
        synced_files = sync_project_to_repo(owner, repo, args.path, args.branch)
        print(f"✓ Synced {len(synced_files)} files to {args.repository}")
    except GitHubError as e:
        print(f"✗ Error: {e}")
    except ValueError:
        print("✗ Error: Repository format should be owner/repo_name")

def cmd_create_and_sync(args):
    """CLI command to create repository and sync project."""
    try:
        result = create_repo_and_sync(args.name, args.description, args.private, args.path, args.org)
        if result:
            print(f"✓ Success! Repository URL: {result['url']}")
        else:
            print("✗ Failed to create repository and sync files")
    except GitHubError as e:
        print(f"✗ Error: {e}")

def cmd_agent_mode(args):
    """CLI command to run in agent mode."""
    agent = initialize_agent_system()
    if not agent:
        return
    
    if args.task:
        run_agent_task(agent, args.task)
    else:
        print("\n🤖 GitHub Agent Mode")
        print("Type your requests in natural language, or 'quit' to exit.")
        print("Examples:")
        print("  - List my repositories")
        print("  - Create a repo called 'my-project'")
        print("  - Upload this project to a new repo")
        print("  - Test if google.com is working")
        print("  - Extract all links from example.com")
        print()
        
        while True:
            try:
                task = input("Agent> ").strip()
                if task.lower() in ['quit', 'exit', 'q']:
                    break
                if task:
                    run_agent_task(agent, task)
            except KeyboardInterrupt:
                print("\n\nExiting agent mode...")
                break

def main():
    parser = argparse.ArgumentParser(description='GitHub Automation System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List repositories
    parser_list = subparsers.add_parser('list', help='List repositories')
    parser_list.set_defaults(func=cmd_list_repos)
    
    # Create repository
    parser_create = subparsers.add_parser('create-repo', help='Create a new repository')
    parser_create.add_argument('name', help='Repository name')
    parser_create.add_argument('--description', default='', help='Repository description')
    parser_create.add_argument('--public', action='store_true', help='Make repository public')
    parser_create.add_argument('--org', help='Organization name (optional)')
    parser_create.add_argument('--private', dest='private', action='store_true', default=True)
    parser_create.set_defaults(func=cmd_create_repo)
    
    # Sync project
    parser_sync = subparsers.add_parser('sync', help='Sync project to existing repository')
    parser_sync.add_argument('repository', help='Repository in format owner/repo_name')
    parser_sync.add_argument('--path', default='.', help='Local path to sync')
    parser_sync.add_argument('--branch', default='main', help='Target branch')
    parser_sync.set_defaults(func=cmd_sync_project)
    
    # Create and sync
    parser_create_sync = subparsers.add_parser('create-and-sync', help='Create repo and sync project')
    parser_create_sync.add_argument('name', help='Repository name')
    parser_create_sync.add_argument('--description', default='', help='Repository description')
    parser_create_sync.add_argument('--public', action='store_true', help='Make repository public')
    parser_create_sync.add_argument('--org', help='Organization name (optional)')
    parser_create_sync.add_argument('--path', default='.', help='Local path to sync')
    parser_create_sync.add_argument('--private', dest='private', action='store_true', default=True)
    parser_create_sync.set_defaults(func=cmd_create_and_sync)
    
    # Agent mode
    parser_agent = subparsers.add_parser('agent', help='Run in agent mode')
    parser_agent.add_argument('--task', help='Single task to run')
    parser_agent.set_defaults(func=cmd_agent_mode)
    
    args = parser.parse_args()
    
    if args.command:
        # Fix private flag for public option
        if hasattr(args, 'public') and args.public:
            args.private = False
        args.func(args)
    else:
        # No command specified, run agent mode
        cmd_agent_mode(type('Args', (), {'task': None})())

if __name__ == "__main__":
    print("=====================================")
    print("  GitHub Automation System v1.0")
    print("=====================================")
    main()
