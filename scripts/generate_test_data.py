"""
Test Data Generator for RAG System
Creates sample data in multiple formats (PDF, JSON, TXT, CSV, SQLite) from various sources
"""

import os
import json
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random


def create_test_data_directory(base_path: str = "data/test_sources") -> str:
    """Create test data directory structure."""
    test_dir = Path(base_path)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for different sources
    (test_dir / "engineering").mkdir(exist_ok=True)
    (test_dir / "hr").mkdir(exist_ok=True)
    (test_dir / "general").mkdir(exist_ok=True)
    (test_dir / "json_sources").mkdir(exist_ok=True)
    (test_dir / "csv_sources").mkdir(exist_ok=True)
    
    return str(test_dir)


def generate_engineering_docs(output_dir: str):
    """Generate engineering documentation samples."""
    eng_dir = Path(output_dir) / "engineering"
    
    # API Documentation
    api_doc = """
# API Documentation

## Database Rollback Procedure

### Overview
The database rollback procedure is used to revert databases to a previous stable state.

### Prerequisites
- Database admin access
- Backup file available
- Estimated downtime: 15-30 minutes

### Step-by-Step Guide

1. **Pre-Rollback Validation**
   - Verify backup integrity
   - Check disk space
   - Notify stakeholders

2. **Execute Rollback**
   ```sql
   RESTORE DATABASE [DBName] FROM DISK = 'backup_path'
   WITH REPLACE, RECOVERY
   ```

3. **Post-Rollback Verification**
   - Verify data integrity
   - Check transaction logs
   - Run sanity tests

### Common Issues
- Issue: Timeout during rollback
  Solution: Increase timeout parameter to 3600 seconds
  
- Issue: Disk space insufficient
  Solution: Move backup to larger drive or clean temp files

### Performance Optimization
- Use SSD for backup/restore operations
- Run during off-peak hours
- Compress backup files for faster transfer
"""
    
    with open(eng_dir / "api_documentation.txt", "w") as f:
        f.write(api_doc)
    
    # Architecture Design
    architecture = """
# Microservices Architecture

## System Components

### 1. API Gateway
- Request routing and authentication
- Rate limiting: 1000 req/s per user
- Response compression

### 2. Service Mesh
- Service-to-service communication
- Load balancing with Kubernetes
- Circuit breaker pattern

### 3. Data Layer
- Primary: PostgreSQL
- Cache: Redis
- Search: Elasticsearch

## Deployment Architecture

Development: Single node Docker container
Staging: Kubernetes cluster (3 nodes)
Production: Kubernetes cluster (10 nodes) with auto-scaling

## Network Topology

```
Internet -> Load Balancer -> API Gateway -> Services -> Database
                                        -> Cache
                                        -> Search
```

## Security Considerations

- TLS 1.3 for all communications
- API key rotation every 90 days
- Database encryption at rest (AES-256)
- VPC isolation per environment
"""
    
    with open(eng_dir / "architecture.txt", "w") as f:
        f.write(architecture)


def generate_hr_docs(output_dir: str):
    """Generate HR documentation samples."""
    hr_dir = Path(output_dir) / "hr"
    
    # Employee Handbook
    handbook = """
# Employee Handbook 2024

## Welcome to ABC Corporation

We are committed to building a diverse, inclusive, and respectful workplace.

## Core Values

1. **Integrity**: Act with honesty and transparency
2. **Innovation**: Embrace change and new ideas
3. **Collaboration**: Work together across teams
4. **Excellence**: Strive for the highest quality

## Working Hours

- Standard hours: 9 AM - 5 PM
- Flexible scheduling available with manager approval
- Core hours: 10 AM - 3 PM (must be present)

## Leave Policy

### Paid Time Off (PTO)
- Annual: 20 days
- Sick leave: 10 days per year
- Bereavement leave: 3-5 days
- Maternity/Paternity: 12 weeks

### Holidays
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving (2 days)
- Christmas
- Additional company holidays (2 days)

## Remote Work Policy

- Eligible employees: 2 days per week remote
- Approval required from manager
- VPN mandatory for security
- Company laptop required

## Professional Development

- Annual training budget: $5,000 per employee
- Conference attendance supported
- Certification reimbursement available
- Internal mentorship program

## Code of Conduct

- Zero tolerance for discrimination
- Respect confidentiality
- Professional communication
- Safety first approach
"""
    
    with open(hr_dir / "employee_handbook.txt", "w") as f:
        f.write(handbook)
    
    # HR Policies
    policies = """
# HR Policies and Procedures

## Performance Management

### Annual Review Process
- Review period: January 1 - December 31
- Self-review: Due December 15
- Manager review: Due January 15
- Rating scale: Exceeds Expectations, Meets Expectations, Below Expectations

### Performance Improvement Plan (PIP)
- Duration: 30-90 days
- Clear metrics and goals
- Weekly check-ins with manager
- Support resources provided

## Compensation Policy

### Salary Structure
- Minimum: $60,000
- Maximum: $150,000
- Based on role, experience, location

### Bonus Structure
- Performance bonus: 10-20% of salary
- Project bonus: For critical deliverables
- Referral bonus: $2,000 per successful hire

### Benefits Package
- Health Insurance: Premiums 80% covered by company
- Dental: 50% coverage
- Vision: 50% coverage
- 401(k): 5% company match

## Disciplinary Procedure

1. **Verbal Warning**: Document in personnel file
2. **Written Warning**: Send formal notice
3. **Suspension**: 1-3 days paid leave for reflection
4. **Termination**: Final notice with severance

## Workplace Safety

- Report all incidents to HR immediately
- Monthly safety training
- Emergency procedures review quarterly
- Workers' compensation coverage for all
"""
    
    with open(hr_dir / "hr_policies.txt", "w") as f:
        f.write(policies)


def generate_general_docs(output_dir: str):
    """Generate general company documentation."""
    gen_dir = Path(output_dir) / "general"
    
    # Company Overview
    overview = """
# ABC Corporation - Company Overview

## About Us

Founded in 2010, ABC Corporation is a leading software solutions provider serving 
1000+ enterprises across North America. We specializing in cloud infrastructure, 
AI/ML solutions, and enterprise software.

## Key Statistics

- Founded: 2010
- Employees: 2,500+
- Offices: 15 locations
- Revenue: $500M+ annually
- Customers: 1000+ enterprise clients

## Our Mission

"Empower organizations with intelligent, scalable technology solutions that drive 
innovation and growth."

## Our Vision

"To be the trusted technology partner for enterprises worldwide, delivering 
solutions that transform businesses."

## Organizational Structure

### Executive Team
- CEO: John Smith
- CTO: Jane Doe
- CFO: Robert Johnson
- COO: Sarah Williams

### Departments
- Engineering (300 people)
- Sales (200 people)
- Customer Success (150 people)
- Finance (50 people)
- Human Resources (30 people)
- Legal (20 people)

## Company Culture

- Innovation-driven environment
- Collaborative teams
- Work-life balance emphasis
- Continuous learning
- Diversity and inclusion

## Contact Information

**Headquarters:**
123 Tech Avenue
San Francisco, CA 94105

**Phone:** 1-800-ABC-CORP
**Email:** info@abccorp.com
**Website:** www.abccorp.com
"""
    
    with open(gen_dir / "company_overview.txt", "w") as f:
        f.write(overview)
    
    # Incident Knowledge Base
    incidents = """
# Incident Knowledge Base

## Critical Incidents from Past 12 Months

### Incident 001: Database Outage - March 2024

**Duration:** 4 hours
**Impact:** Complete service unavailability
**Root Cause:** Disk space exhaustion on primary database

**Resolution Steps:**
1. Identified disk space issue (98% full)
2. Cleared old logs and backups (freed 500GB)
3. Restarted database services
4. Restored from WAL files

**Prevention:**
- Automated disk monitoring with 80% alert threshold
- Automated log cleanup scripts
- Capacity planning review quarterly

### Incident 002: API Rate Limiting Bug - May 2024

**Duration:** 2 hours
**Impact:** Intermittent API failures for 50 customers
**Root Cause:** Rate limiter counter not reset in Redis

**Resolution Steps:**
1. Deployed hotfix to API gateway
2. Cleared Redis cache
3. Monitored error rates for 1 hour
4. Full rollback if needed (not needed)

**Prevention:**
- Improved Redis key TTL management
- Added automated tests for rate limiter
- Monitoring dashboard for rate limit hits

### Incident 003: Memory Leak - July 2024

**Duration:** 6 hours
**Impact:** Gradual service degradation
**Root Cause:** Unclosed database connections in worker nodes

**Resolution Steps:**
1. Identified memory leak through monitoring
2. Restarted affected worker pods
3. Deployed code fix
4. Monitored memory usage for 24 hours

**Prevention:**
- Connection pool automated cleanup
- Memory profiling in CI/CD
- Alerts for memory usage trending up
"""
    
    with open(gen_dir / "incident_kb.txt", "w") as f:
        f.write(incidents)


def generate_json_sources(output_dir: str):
    """Generate JSON test data."""
    json_dir = Path(output_dir) / "json_sources"
    
    # Product catalog
    products = {
        "products": [
            {
                "id": "prod_001",
                "name": "CloudSync Pro",
                "category": "infrastructure",
                "description": "Enterprise cloud synchronization platform",
                "pricing": {
                    "monthly": 299,
                    "annual": 2990
                },
                "features": [
                    "Real-time sync",
                    "End-to-end encryption",
                    "API access",
                    "24/7 support"
                ]
            },
            {
                "id": "prod_002",
                "name": "DataMind AI",
                "category": "analytics",
                "description": "AI-powered data analytics and insights",
                "pricing": {
                    "monthly": 499,
                    "annual": 4990
                },
                "features": [
                    "ML models included",
                    "Real-time dashboards",
                    "Predictive analytics",
                    "Custom training"
                ]
            }
        ]
    }
    
    with open(json_dir / "products.json", "w") as f:
        json.dump(products, f, indent=2)
    
    # Customers data
    customers = {
        "customers": [
            {
                "id": "cust_001",
                "name": "Tech Startup Inc",
                "industry": "SaaS",
                "founded": 2015,
                "employees": 50,
                "products_using": ["CloudSync Pro"],
                "annual_spend": 5980,
                "support_tier": "Premium"
            },
            {
                "id": "cust_002",
                "name": "Enterprise Corp",
                "industry": "Financial Services",
                "founded": 1995,
                "employees": 5000,
                "products_using": ["CloudSync Pro", "DataMind AI"],
                "annual_spend": 29950,
                "support_tier": "Enterprise"
            }
        ]
    }
    
    with open(json_dir / "customers.json", "w") as f:
        json.dump(customers, f, indent=2)


def generate_csv_sources(output_dir: str):
    """Generate CSV test data."""
    csv_dir = Path(output_dir) / "csv_sources"
    
    # Sales data
    sales_data = [
        ["date", "product_id", "customer_id", "amount", "region", "status"],
        ["2024-01-15", "prod_001", "cust_001", 299, "US-West", "completed"],
        ["2024-01-20", "prod_002", "cust_002", 4990, "US-East", "completed"],
        ["2024-02-10", "prod_001", "cust_003", 299, "EU-Central", "pending"],
        ["2024-02-15", "prod_002", "cust_001", 499, "US-West", "completed"],
        ["2024-03-05", "prod_001", "cust_002", 2990, "US-East", "completed"],
    ]
    
    with open(csv_dir / "sales_data.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(sales_data)
    
    # Employee directory
    employees = [
        ["employee_id", "name", "role", "department", "salary", "hire_date"],
        ["emp_001", "Alice Johnson", "Senior Engineer", "Engineering", 150000, "2018-03-15"],
        ["emp_002", "Bob Smith", "Product Manager", "Product", 120000, "2019-06-01"],
        ["emp_003", "Carol White", "HR Manager", "Human Resources", 90000, "2020-01-10"],
        ["emp_004", "David Brown", "Sales Lead", "Sales", 110000, "2017-11-20"],
        ["emp_005", "Eve Wilson", "Junior Engineer", "Engineering", 80000, "2023-07-15"],
    ]
    
    with open(csv_dir / "employees.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(employees)


def generate_sqlite_knowledge_base(output_dir: str):
    """Generate SQLite3 knowledge base with structured information."""
    sqlite_dir = Path(output_dir) / "sqlite_sources"
    sqlite_dir.mkdir(exist_ok=True)
    
    db_path = sqlite_dir / "knowledge_base.db"
    
    # Remove old database if exists
    if db_path.exists():
        os.remove(db_path)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create knowledge_base table
    cursor.execute("""
        CREATE TABLE knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert knowledge base articles
    knowledge_articles = [
        (
            "Database Performance Tuning",
            """Database performance is critical for application responsiveness. Key areas:
            
1. Indexing Strategy
   - Primary keys should be unique identifiers
   - Foreign keys need indexes for join performance
   - Composite indexes for multi-column WHERE clauses
   
2. Query Optimization
   - Use EXPLAIN PLAN to analyze queries
   - Avoid N+1 query patterns
   - Batch operations when possible
   
3. Connection Pooling
   - Maintain pool size between 5-20 connections
   - Set connection timeout to 30 seconds
   - Monitor pool utilization metrics""",
            "engineering",
            "performance,database,optimization"
        ),
        (
            "Code Review Best Practices",
            """Effective code reviews improve code quality and knowledge sharing.
            
Standards for Reviews:
- Check for security vulnerabilities
- Verify test coverage (>80%)
- Ensure documentation is updated
- Validate error handling
- Review performance implications

Reviewer Responsibilities:
- Respond within 24 hours
- Be constructive and respectful
- Provide actionable feedback
- Approve only when confident

Common Issues Found:
- Missing null checks
- SQL injection vulnerabilities
- Hardcoded credentials
- Missing error logging""",
            "engineering",
            "code-review,best-practices,quality"
        ),
        (
            "Employee Onboarding Process",
            """New employee onboarding ensures smooth integration into the team.
            
Week 1: Orientation
- Company overview and mission
- IT setup (laptop, accounts, access)
- Team introductions
- Office tour
- Emergency procedures

Week 2: Role Training
- Role-specific documentation
- Tool training (IDE, databases, frameworks)
- Project overview
- Mentor assignment

Week 3-4: Ramp Up
- Assigned first tasks
- Code review participation
- Team meeting attendance
- Mid-onboarding check-in

Completion: 90-Day Review
- Performance assessment
- Feedback session
- Benefits enrollment confirmation""",
            "hr",
            "onboarding,people,process"
        ),
        (
            "Company Security Policy",
            """Data security is everyone's responsibility.
            
Password Requirements:
- Minimum 12 characters
- Must include uppercase, lowercase, numbers, special chars
- Change every 90 days
- Never share passwords
- Use password manager

Data Classification:
- Public: Can be shared externally
- Internal: For company use only
- Confidential: Limited access
- Restricted: Legal/financial data

Incident Response:
- Report security issues to security@company.com
- Do not attempt to investigate unauthorized access
- Preserve evidence (logs, screenshots)
- Follow up within 24 hours""",
            "security",
            "security,policy,data-protection"
        ),
        (
            "Product Roadmap Q1 2025",
            """Strategic initiatives for Q1 2025 focus on scalability and user experience.
            
Feature Development:
- Implement real-time notifications (2 weeks)
- Add mobile app beta (4 weeks)
- Upgrade database infrastructure (3 weeks)
- Performance optimization (ongoing)

User Experience:
- Dashboard redesign (20 hours)
- Mobile responsive UI (15 hours)
- Accessibility improvements (10 hours)

Infrastructure:
- Migrate to Kubernetes (6 weeks)
- Implement auto-scaling (2 weeks)
- Add monitoring/alerting (1 week)

Quality:
- Automated test coverage to 90%
- Load testing at 10K concurrent users
- Security audit and penetration testing""",
            "general",
            "roadmap,planning,strategy"
        )
    ]
    
    for title, content, category, tags in knowledge_articles:
        cursor.execute(
            """INSERT INTO knowledge_base (title, content, category, tags) 
               VALUES (?, ?, ?, ?)""",
            (title, content, category, tags)
        )
    
    # Create incidents table
    cursor.execute("""
        CREATE TABLE incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_date TIMESTAMP,
            assigned_to TEXT
        )
    """)
    
    incidents = [
        (
            "Database connection timeout",
            "Intermittent database connection timeouts observed in production. Response times spike to 5+ seconds. Affects 2% of requests.",
            "high",
            "resolved",
            datetime.now() - timedelta(days=5),
            datetime.now() - timedelta(days=3),
            "Alice Johnson"
        ),
        (
            "Memory leak in caching service",
            "Memory usage of cache service grows 200MB/hour. Requires restart every 6 hours.",
            "critical",
            "investigating",
            datetime.now() - timedelta(days=2),
            None,
            "Bob Smith"
        ),
        (
            "API rate limiting not working",
            "Rate limiter not properly throttling requests from single client. One client making 100K requests/second.",
            "high",
            "in-progress",
            datetime.now() - timedelta(hours=6),
            None,
            "Carol White"
        )
    ]
    
    for title, desc, severity, status, created, resolved, assigned in incidents:
        cursor.execute(
            """INSERT INTO incidents (title, description, severity, status, created_date, resolved_date, assigned_to)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, desc, severity, status, created, resolved, assigned)
        )
    
    # Create procedures table
    cursor.execute("""
        CREATE TABLE procedures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            steps TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    procedures = [
        (
            "Incident Response",
            "Process for responding to production incidents",
            """1. Detection - Automated alerts or user reports
2. Triage - Assess severity (P1=Critical, P2=High, P3=Medium, P4=Low)
3. Notification - Alert on-call engineer
4. Investigation - Determine root cause
5. Remediation - Implement fix
6. Communication - Update status page
7. Post-mortem - Document learnings
8. Prevention - Implement preventive measures"""
        ),
        (
            "Database Backup and Recovery",
            "Process for backing up and recovering databases",
            """1. Schedule - Daily at 2 AM UTC
2. Backup - Create full backup to S3
3. Verification - Test restore in staging
4. Retention - Keep 30 days of backups
5. Recovery - Contact DBA for restore
6. Validation - Verify data integrity
7. Communication - Notify stakeholders"""
        ),
        (
            "Deployment Process",
            "Standard process for deploying to production",
            """1. Build - Compile and test locally
2. Stage - Deploy to staging environment
3. Smoke Test - Run automated tests
4. Review - Code and ops review
5. Approval - Get business approval
6. Schedule - Pick maintenance window
7. Deploy - Deploy to production (blue-green)
8. Verify - Monitor health checks
9. Notify - Update team"""
        )
    ]
    
    for name, desc, steps in procedures:
        cursor.execute(
            """INSERT INTO procedures (name, description, steps)
               VALUES (?, ?, ?)""",
            (name, desc, steps)
        )
    
    conn.commit()
    conn.close()
    
    return str(db_path)


def main():
    """Generate all test data."""
    print("[*] Generating test data...")
    
    test_dir = create_test_data_directory()
    print(f"[OK] Created test data directory: {test_dir}")
    
    print("[+] Generating engineering docs...")
    generate_engineering_docs(test_dir)
    
    print("[+] Generating HR docs...")
    generate_hr_docs(test_dir)
    
    print("[+] Generating general docs...")
    generate_general_docs(test_dir)
    
    print("[+] Generating JSON sources...")
    generate_json_sources(test_dir)
    
    print("[+] Generating CSV sources...")
    generate_csv_sources(test_dir)
    
    print("[+] Generating SQLite knowledge base...")
    db_path = generate_sqlite_knowledge_base(test_dir)
    print(f"    Created: {db_path}")
    
    print(f"\n[OK] Test data generation complete!")
    print(f"[OK] Test data location: {test_dir}")
    print("\nGenerated files:")
    for root, dirs, files in os.walk(test_dir):
        level = root.replace(test_dir, "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")


if __name__ == "__main__":
    main()
