"""
Agent Thought Process Visualizer
Renders agent decision-making and reasoning in human-readable format
Includes animated display with graphics and delays for visual appeal
"""
import json
import time
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ThoughtStep:
    """Single step in agent's thought process"""
    step_number: int
    title: str
    description: str
    status: str  # 'active', 'completed', 'pending', 'error'
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None


class ThoughtProcess:
    """Tracks and visualizes an agent's thought process"""
    
    def __init__(self, agent_name: str, operation: str):
        self.agent_name = agent_name
        self.operation = operation
        self.steps: List[ThoughtStep] = []
        self.start_time = datetime.now()
        self.current_step = 0
        self.metadata: Dict[str, Any] = {}
    
    def add_step(self, title: str, description: str, details: Optional[Dict] = None) -> int:
        """Add a thought step"""
        step = ThoughtStep(
            step_number=len(self.steps) + 1,
            title=title,
            description=description,
            status='pending',
            details=details
        )
        self.steps.append(step)
        return step.step_number - 1
    
    def start_step(self, step_index: int, details: Optional[Dict] = None):
        """Mark step as active"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = 'active'
            self.current_step = step_index
            if details:
                self.steps[step_index].details = details
    
    def complete_step(self, step_index: int, duration_ms: Optional[int] = None):
        """Mark step as completed"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = 'completed'
            self.steps[step_index].duration_ms = duration_ms
    
    def error_step(self, step_index: int, error_msg: str):
        """Mark step as errored"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = 'error'
            self.steps[step_index].details = {'error': error_msg}
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata about the operation"""
        self.metadata[key] = value
    
    def visualize_simple(self) -> str:
        """Simple ASCII visualization"""
        lines = []
        lines.append("\n" + "="*70)
        lines.append(f"🧠 {self.agent_name} | {self.operation}")
        lines.append("="*70)
        
        for i, step in enumerate(self.steps):
            status_icon = self._get_status_icon(step.status)
            indent = "  " if step.status == 'pending' else "  "
            
            lines.append(f"\n{status_icon} [{step.step_number}] {step.title}")
            lines.append(f"{indent}└─ {step.description}")
            
            if step.details and step.status != 'pending':
                for key, value in step.details.items():
                    if isinstance(value, (dict, list)):
                        lines.append(f"{indent}   • {key}: {json.dumps(value, indent=2)[:100]}...")
                    else:
                        lines.append(f"{indent}   • {key}: {value}")
            
            if step.duration_ms:
                lines.append(f"{indent}   ⏱ {step.duration_ms}ms")
        
        if self.metadata:
            lines.append("\n📊 Metadata:")
            for key, value in self.metadata.items():
                lines.append(f"  • {key}: {value}")
        
        lines.append("\n" + "="*70 + "\n")
        return "\n".join(lines)
    
    def visualize_detailed(self) -> str:
        """Detailed visualization with all information"""
        lines = []
        lines.append("\n" + "█"*70)
        lines.append(f"█ 🧠 AGENT THOUGHT PROCESS: {self.agent_name}")
        lines.append(f"█ 📋 Operation: {self.operation}")
        lines.append(f"█ ⏰ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("█"*70)
        
        for step in self.steps:
            lines.append(self._format_detailed_step(step))
        
        if self.metadata:
            lines.append("\n" + "─"*70)
            lines.append("📊 OPERATION METADATA:")
            lines.append("─"*70)
            for key, value in self.metadata.items():
                lines.append(f"  {key:20s}: {self._format_value(value)}")
        
        # Summary
        completed = len([s for s in self.steps if s.status == 'completed'])
        total = len(self.steps)
        lines.append("\n" + "─"*70)
        lines.append(f"✅ Progress: {completed}/{total} steps completed")
        lines.append("─"*70 + "\n")
        
        return "\n".join(lines)
    
    def visualize_flowchart(self) -> str:
        """ASCII flowchart visualization"""
        lines = []
        lines.append("\n" + "╔" + "═"*68 + "╗")
        lines.append(f"║ 🧠 {self.agent_name:30s} {self.operation:35s} ║")
        lines.append("╚" + "═"*68 + "╝")
        
        for i, step in enumerate(self.steps):
            is_last = i == len(self.steps) - 1
            
            # Main box
            icon = self._get_status_icon(step.status)
            lines.append(f"    ┌{'─'*50}┐")
            lines.append(f"    │ {icon} [{step.step_number}] {step.title:42s} │")
            lines.append(f"    │ {step.description:50s} │")
            lines.append(f"    └{'─'*50}┘")
            
            if not is_last:
                lines.append("         ▼")
        
        lines.append("\n")
        return "\n".join(lines)
    
    def visualize_tree(self) -> str:
        """Tree-style visualization"""
        lines = []
        lines.append("\n" + "🧠 " + self.agent_name)
        lines.append("└─ " + self.operation)
        
        for i, step in enumerate(self.steps):
            is_last = i == len(self.steps) - 1
            prefix = "   └─ " if is_last else "   ├─ "
            status = self._get_status_icon(step.status)
            
            lines.append(f"{prefix}{status} [{step.step_number}] {step.title}")
            
            if step.details:
                for key, value in step.details.items():
                    detail_prefix = "        └─ " if is_last else "       ├─ "
                    lines.append(f"{detail_prefix}• {key}: {self._format_value(value, 40)}")
        
        lines.append("\n")
        return "\n".join(lines)
    
    def animate_simple(self, delay: float = 0.5):
        """Animated simple visualization with delays"""
        # Header
        print("\n" + "="*70)
        time.sleep(delay * 0.5)
        print(f"🧠 {self.agent_name} | {self.operation}")
        time.sleep(delay * 0.3)
        print("="*70)
        time.sleep(delay)
        
        # Steps
        for i, step in enumerate(self.steps):
            status_icon = self._get_status_icon(step.status)
            
            # Print step title
            print(f"\n{status_icon} [{step.step_number}] {step.title}")
            time.sleep(delay * 0.3)
            
            # Print description
            print(f"  └─ {step.description}")
            time.sleep(delay * 0.2)
            
            # Print details
            if step.details and step.status != 'pending':
                for key, value in step.details.items():
                    if isinstance(value, (dict, list)):
                        print(f"     • {key}: {json.dumps(value, indent=2)[:60]}...")
                    else:
                        print(f"     • {key}: {value}")
                    time.sleep(delay * 0.15)
            
            # Print duration
            if step.duration_ms:
                print(f"     ⏱ {step.duration_ms}ms")
                time.sleep(delay * 0.1)
        
        # Metadata
        if self.metadata:
            print("\n📊 Metadata:")
            time.sleep(delay * 0.3)
            for key, value in self.metadata.items():
                print(f"  • {key}: {value}")
                time.sleep(delay * 0.15)
        
        print("\n" + "="*70 + "\n")
        time.sleep(delay * 0.3)
    
    def animate_detailed(self, delay: float = 0.5):
        """Animated detailed visualization"""
        # Header with blocks
        print("\n" + "█"*70)
        time.sleep(delay * 0.5)
        print(f"█ 🧠 AGENT THOUGHT PROCESS: {self.agent_name}")
        time.sleep(delay * 0.3)
        print(f"█ 📋 Operation: {self.operation}")
        time.sleep(delay * 0.3)
        print(f"█ ⏰ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(delay * 0.3)
        print("█"*70)
        time.sleep(delay)
        
        # Steps
        for step in self.steps:
            print("\n" + "─"*70)
            time.sleep(delay * 0.3)
            status_icon = self._get_status_icon(step.status)
            print(f"{status_icon} STEP {step.step_number}: {step.title}")
            time.sleep(delay * 0.2)
            print("─"*70)
            time.sleep(delay * 0.1)
            
            print(f"Description: {step.description}")
            time.sleep(delay * 0.2)
            
            # Status
            if step.status == 'active':
                print("Status: 🔄 ACTIVE (In Progress)")
            elif step.status == 'completed':
                duration_str = f"({step.duration_ms}ms)" if step.duration_ms else ""
                print(f"Status: ✅ COMPLETED {duration_str}")
            elif step.status == 'error':
                print("Status: ❌ ERROR")
            else:
                print("Status: ⏳ PENDING")
            
            time.sleep(delay * 0.2)
            
            # Details
            if step.details:
                print("\nDetails:")
                time.sleep(delay * 0.15)
                for key, value in step.details.items():
                    print(f"  • {key}: {self._format_value(value)}")
                    time.sleep(delay * 0.1)
        
        # Metadata
        if self.metadata:
            print("\n" + "─"*70)
            print("📊 OPERATION METADATA:")
            print("─"*70)
            time.sleep(delay * 0.3)
            for key, value in self.metadata.items():
                print(f"  {key:20s}: {self._format_value(value)}")
                time.sleep(delay * 0.1)
        
        # Summary
        completed = len([s for s in self.steps if s.status == 'completed'])
        total = len(self.steps)
        print("\n" + "─"*70)
        time.sleep(delay * 0.2)
        print(f"✅ Progress: {completed}/{total} steps completed")
        print("─"*70 + "\n")
        time.sleep(delay * 0.3)
    
    def animate_spinner(self, delay: float = 0.5):
        """Show animated spinner while processing"""
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        
        print(f"\n🧠 {self.agent_name} is thinking...")
        sys.stdout.flush()
        
        # Show spinner for each step
        for step in self.steps:
            for i in range(4):  # Show spinner 4 times per step
                sys.stdout.write(f"\r{spinners[i % len(spinners)]} {step.title}")
                sys.stdout.flush()
                time.sleep(delay * 0.25)
            
            # Mark as complete
            print(f"\r✅ {step.title}")
            time.sleep(delay * 0.2)
    
    def animate_progress_bar(self, delay: float = 0.5):
        """Show animated progress bar"""
        print(f"\n🧠 {self.agent_name} | {self.operation}")
        print("Processing steps...\n")
        time.sleep(delay * 0.3)
        
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps):
            # Progress bar
            progress = (i + 1) / total_steps
            bar_length = 50
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            percentage = int(progress * 100)
            print(f"[{bar}] {percentage}%")
            print(f"  {self._get_status_icon(step.status)} {step.title}")
            
            time.sleep(delay)
            sys.stdout.write("\033[F\033[F")  # Move cursor up 2 lines
            sys.stdout.flush()
        
        # Final bar
        bar = "█" * bar_length
        print(f"[{bar}] 100%")
        print(f"  ✅ All steps completed!")
        print("\n")
        time.sleep(delay * 0.3)
    
    def animate_cascading(self, delay: float = 0.5):
        """Cascade animation - steps appear sequentially"""
        print("\n" + "="*70)
        print(f"🧠 {self.agent_name}")
        print("="*70)
        time.sleep(delay * 0.5)
        
        for i, step in enumerate(self.steps):
            # Cascade effect - indent increases then decreases
            indent = "  " * (i + 1) if i < len(self.steps) // 2 else "  " * (len(self.steps) - i)
            
            status = self._get_status_icon(step.status)
            print(f"{indent}↳ {status} {step.title}")
            time.sleep(delay * 0.4)
            
            print(f"{indent}  └─ {step.description}")
            time.sleep(delay * 0.3)
            
            if step.duration_ms:
                print(f"{indent}  ⏱ {step.duration_ms}ms")
                time.sleep(delay * 0.2)
        
        print("\n" + "="*70 + "\n")
        time.sleep(delay * 0.3)
    
    def animate_matrix_style(self, delay: float = 0.1):
        """Matrix-style animation with character fade-in"""
        chars = "░▒▓█"
        
        print(f"\n🧠 {self.agent_name} | {self.operation}")
        print()
        
        for step in self.steps:
            title_text = f"  [{step.step_number}] {step.title}"
            
            # Animate character by character
            for char_idx in range(len(title_text)):
                sys.stdout.write(title_text[:char_idx+1])
                sys.stdout.flush()
                time.sleep(delay * 0.1)
            
            print()
            time.sleep(delay * 0.5)
        
        print("\n" + "="*70 + "\n")
    
    @staticmethod
    def _get_status_icon(status: str) -> str:
        """Get icon for status"""
        icons = {
            'completed': '✅',
            'active': '🔄',
            'pending': '⏳',
            'error': '❌'
        }
        return icons.get(status, '❓')
    
    @staticmethod
    def _format_detailed_step(step: ThoughtStep) -> str:
        """Format a step for detailed view"""
        lines = []
        status_icon = ThoughtProcess._get_status_icon(step.status)
        
        lines.append("\n" + "─"*70)
        lines.append(f"{status_icon} STEP {step.step_number}: {step.title}")
        lines.append("─"*70)
        lines.append(f"Description: {step.description}")
        
        if step.status == 'active':
            lines.append("Status: 🔄 ACTIVE (In Progress)")
        elif step.status == 'completed':
            lines.append(f"Status: ✅ COMPLETED ({step.duration_ms}ms)" if step.duration_ms else "Status: ✅ COMPLETED")
        elif step.status == 'error':
            lines.append("Status: ❌ ERROR")
        else:
            lines.append("Status: ⏳ PENDING")
        
        if step.details:
            lines.append("\nDetails:")
            for key, value in step.details.items():
                lines.append(f"  • {key}: {ThoughtProcess._format_value(value)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_value(value: Any, max_len: int = 100) -> str:
        """Format a value for display"""
        if isinstance(value, dict):
            return json.dumps(value)[:max_len]
        elif isinstance(value, list):
            if len(value) > 5:
                return f"[{', '.join(str(v) for v in value[:5])} ... +{len(value)-5} more]"
            return str(value)
        else:
            s = str(value)
            return s if len(s) <= max_len else s[:max_len-3] + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary"""
        return {
            'agent': self.agent_name,
            'operation': self.operation,
            'started': self.start_time.isoformat(),
            'steps': [asdict(step) for step in self.steps],
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Export as JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)


class ThoughtVisualizer:
    """Global thought process management"""
    
    _processes: Dict[str, ThoughtProcess] = {}
    
    @classmethod
    def create_process(cls, agent_name: str, operation: str) -> ThoughtProcess:
        """Create a new thought process tracker"""
        process = ThoughtProcess(agent_name, operation)
        key = f"{agent_name}:{operation}:{datetime.now().timestamp()}"
        cls._processes[key] = process
        return process
    
    @classmethod
    def get_current_processes(cls) -> Dict[str, ThoughtProcess]:
        """Get all current processes"""
        return cls._processes
    
    @classmethod
    def clear_processes(cls):
        """Clear all processes"""
        cls._processes.clear()
