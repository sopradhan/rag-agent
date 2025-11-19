#!/usr/bin/env python
"""
RAG Agent System Initialization Script
Sets up the complete system: dependencies, databases, test data, and configuration
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.sqlite_storage import RAGDatabase
from scripts.generate_test_data import main as generate_test_data


class RAGSystemInitializer:
    """Initialize RAG Agent system."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.config_dir = self.base_path / "config"
        self.data_dir = self.base_path / "data"
        self.scripts_dir = self.base_path / "scripts"
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def install_dependencies(self):
        """Install Python dependencies."""
        self.print_header("STEP 1: Installing Dependencies")
        
        requirements_file = self.base_path / "requirements.txt"
        if not requirements_file.exists():
            print("[ERROR] requirements.txt not found!")
            return False
        
        print(f"[*] Installing packages from {requirements_file}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "-r", str(requirements_file),
                "--quiet"
            ])
            print("[OK] Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install dependencies: {e}")
            return False
    
    def create_directories(self):
        """Create necessary directory structure."""
        self.print_header("STEP 2: Creating Directory Structure")
        
        dirs_to_create = [
            self.data_dir,
            self.data_dir / "chroma_db",
            self.data_dir / "test_sources",
            self.config_dir,
            self.scripts_dir,
            self.base_path / "logs",
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Created: {dir_path}")
        
        return True
    
    def initialize_database(self):
        """Initialize SQLite database with hierarchical RBAC."""
        self.print_header("STEP 3: Initializing Database (Hierarchical RBAC)")
        
        try:
            print("[*] Initializing RAGDatabase...")
            db = RAGDatabase()
            print("[OK] Database initialized with all tables")
            
            # Initialize sample data
            self._initialize_sample_rbac(db)
            
            return True
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _initialize_sample_rbac(self, db: RAGDatabase):
        """Initialize sample RBAC hierarchy."""
        print("[*] Initializing sample RBAC hierarchy...")
        
        cursor = db.conn.cursor()
        
        # Create sample company
        try:
            cursor.execute("""
                INSERT INTO company (name, domain) 
                VALUES (?, ?)
            """, ("Sample Corp", "sample.com"))
            company_id = cursor.lastrowid
            print(f"  [OK] Created company: Sample Corp (ID: {company_id})")
            
            # Create departments
            cursor.execute("""
                INSERT INTO department (company_id, name, level) 
                VALUES (?, ?, ?)
            """, (company_id, "Engineering", 0))
            eng_dept_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO department (company_id, name, level) 
                VALUES (?, ?, ?)
            """, (company_id, "Human Resources", 0))
            hr_dept_id = cursor.lastrowid
            
            print(f"  [OK] Created departments: Engineering, Human Resources")
            
            # Create roles
            cursor.execute("""
                INSERT INTO role (department_id, role_name, role_type, grade)
                VALUES (?, ?, ?, ?)
            """, (eng_dept_id, "Software Engineer", "engineer", "L3"))
            eng_role_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO role (department_id, role_name, role_type, grade)
                VALUES (?, ?, ?, ?)
            """, (hr_dept_id, "HR Manager", "hr", "L3"))
            hr_role_id = cursor.lastrowid
            
            print(f"  [OK] Created roles: Software Engineer, HR Manager")
            
            # Create sample users
            cursor.execute("""
                INSERT INTO users (username, email, company_id, department_id, role_id)
                VALUES (?, ?, ?, ?, ?)
            """, ("engineer@sample.com", "engineer@sample.com", company_id, eng_dept_id, eng_role_id))
            
            cursor.execute("""
                INSERT INTO users (username, email, company_id, department_id, role_id)
                VALUES (?, ?, ?, ?, ?)
            """, ("hr@sample.com", "hr@sample.com", company_id, hr_dept_id, hr_role_id))
            
            print(f"  [OK] Created sample users")
            
            db.conn.commit()
            print("[OK] Sample RBAC hierarchy initialized")
        
        except Exception as e:
            print(f"[WARN] Could not initialize sample RBAC: {e}")
            db.conn.rollback()
    
    def generate_test_data(self):
        """Generate test data from multiple sources."""
        self.print_header("STEP 4: Generating Test Data")
        
        try:
            print("[*] Generating test data (TXT, JSON, CSV)...")
            # Change to script directory for relative paths
            original_cwd = os.getcwd()
            os.chdir(self.base_path)
            
            generate_test_data()
            
            os.chdir(original_cwd)
            return True
        except Exception as e:
            print(f"[ERROR] Test data generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_env_file(self):
        """Create .env configuration file."""
        self.print_header("STEP 5: Creating Configuration")
        
        env_file = self.base_path / ".env"
        
        if env_file.exists():
            print("[SKIP] .env file already exists")
            return True
        
        env_content = """# RAG Agent System Configuration
# Generated on {timestamp}

# Ollama Configuration
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434

# ChromaDB Configuration
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_PERSISTENT_DIR=./data/chroma_db

# SQLite Configuration
DATABASE_PATH=./data/rag_system.db

# Embeddings Configuration
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
EMBEDDINGS_DIMENSION=384

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/rag_system.log

# LLM Configuration
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9
LLM_MAX_TOKENS=2000
""".format(timestamp=datetime.now().isoformat())
        
        with open(env_file, "w") as f:
            f.write(env_content)
        
        print(f"[OK] Created .env file: {env_file}")
        return True
    
    def verify_installation(self):
        """Verify the installation."""
        self.print_header("STEP 6: Verifying Installation")
        
        try:
            # Check imports
            print("[*] Checking core imports...")
            from src.orchestrator import MasterOrchestrator
            from src.storage import RAGDatabase, ChromaVectorStore
            from src.subagents.langchain_subagents import (
                AnalyzerSubagent, SearcherSubagent, FilterSubagent
            )
            print("[OK] All core modules imported successfully")
            
            # Check databases
            print("[*] Checking databases...")
            db = RAGDatabase()
            cursor = db.conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            print(f"[OK] Database ready with {table_count} tables")
            
            # Check test data
            print("[*] Checking test data...")
            test_dir = self.data_dir / "test_sources"
            if test_dir.exists():
                file_count = sum(1 for _ in test_dir.rglob("*") if _.is_file())
                print(f"[OK] Test data ready with {file_count} files")
            
            return True
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            return False
    
    def print_summary(self, success: bool):
        """Print installation summary."""
        self.print_header("INSTALLATION SUMMARY")
        
        if success:
            print("[OK] RAG Agent System Successfully Initialized!")
            print("\nNext steps:")
            print("1. Start Ollama: ollama serve")
            print("2. Pull model: ollama pull llama3.2:latest")
            print("3. Start dashboard: streamlit run dashboard.py")
            print("4. Access at: http://localhost:8501")
            print("\nConfiguration:")
            print(f"  * Config directory: {self.config_dir}")
            print(f"  * Data directory: {self.data_dir}")
            print(f"  * Database: {self.data_dir / 'rag_system.db'}")
            print(f"  * Test data: {self.data_dir / 'test_sources'}")
            print("\nDocumentation:")
            print("  * Read README.md for usage")
            print("  * Check INSTALLATION.md for detailed setup")
            return 0
        else:
            print("[ERROR] Installation encountered errors. Please check logs above.")
            return 1
    
    def run(self, skip_dependencies: bool = False):
        """Run complete initialization."""
        self.print_header("RAG AGENT SYSTEM INITIALIZATION")
        
        steps = [
            ("Dependencies", self.install_dependencies, not skip_dependencies),
            ("Directories", self.create_directories, True),
            ("Database", self.initialize_database, True),
            ("Test Data", self.generate_test_data, True),
            ("Environment", self.create_env_file, True),
            ("Verification", self.verify_installation, True),
        ]
        
        success = True
        for step_name, step_func, should_run in steps:
            if not should_run:
                continue
            try:
                if not step_func():
                    success = False
                    print(f"[ERROR] {step_name} step failed!")
                    break
            except Exception as e:
                print(f"[ERROR] {step_name} step failed: {e}")
                import traceback
                traceback.print_exc()
                success = False
                break
        
        return self.print_summary(success)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize RAG Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full initialization
  python initialize.py
  
  # Skip pip install (if already installed)
  python initialize.py --skip-dependencies
  
  # Initialize at specific location
  python initialize.py --path /path/to/project
        """
    )
    
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Skip pip install step"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Base path for initialization (default: current directory)"
    )
    
    args = parser.parse_args()
    
    initializer = RAGSystemInitializer(base_path=args.path)
    return initializer.run(skip_dependencies=args.skip_dependencies)


if __name__ == "__main__":
    sys.exit(main())
