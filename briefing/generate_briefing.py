#!/usr/bin/env python3
"""
CEO Weekly Briefing Generator
Gold Tier - AI Employee System
"""

from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json

class BriefingGenerator:
    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.done_folder = self.vault_path / 'Done'
        self.approved_folder = self.vault_path / 'Approved'
        self.rejected_folder = self.vault_path / 'Rejected'
        self.briefing_folder = self.vault_path / 'briefing' / 'reports'
        
        self.briefing_folder.mkdir(parents=True, exist_ok=True)
    
    def analyze_messages(self, start_date=None, end_date=None):
        """Analyze all processed messages"""
        
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        stats = {
            'total': 0,
            'by_channel': defaultdict(int),
            'by_priority': defaultdict(int),
            'by_status': defaultdict(int),
            'flagged': 0,
            'with_amounts': [],
            'high_priority_messages': []
        }
        
        # Analyze all folders
        folders = [
            (self.done_folder, 'Processed'),
            (self.approved_folder, 'Approved'),
            (self.rejected_folder, 'Rejected')
        ]
        
        for folder, status in folders:
            if not folder.exists():
                continue
            
            for md_file in folder.glob('*.md'):
                try:
                    content = md_file.read_text()
                    
                    # Parse frontmatter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            metadata = {}
                            for line in parts[1].strip().split('\n'):
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    metadata[key.strip()] = value.strip().strip('"')
                            
                            stats['total'] += 1
                            
                            # Channel
                            filename = md_file.name
                            if filename.startswith('EMAIL_'):
                                stats['by_channel']['Gmail'] += 1
                            elif filename.startswith('LINKEDIN_'):
                                stats['by_channel']['LinkedIn'] += 1
                            elif filename.startswith('WHATSAPP_'):
                                stats['by_channel']['WhatsApp'] += 1
                            
                            # Priority
                            priority = metadata.get('priority', 'NORMAL')
                            stats['by_priority'][priority] += 1
                            
                            # Status
                            stats['by_status'][status] += 1
                            
                            # High priority tracking
                            if priority == 'HIGH':
                                stats['high_priority_messages'].append({
                                    'from': metadata.get('from', 'Unknown'),
                                    'subject': metadata.get('subject', 'No subject'),
                                    'channel': filename.split('_')[0],
                                    'status': status
                                })
                
                except Exception as e:
                    print(f"Error processing {md_file.name}: {e}")
        
        return stats
    
    def generate_markdown_report(self, stats):
        """Generate markdown briefing"""
        
        week_end = datetime.now()
        week_start = week_end - timedelta(days=7)
        
        report = f"""# 📊 AI Employee - Weekly Briefing

**Period:** {week_start.strftime('%B %d, %Y')} - {week_end.strftime('%B %d, %Y')}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 Executive Summary

### Overall Activity
- **Total Messages Processed:** {stats['total']}
- **High Priority Items:** {stats['by_priority'].get('HIGH', 0)}
- **Medium Priority Items:** {stats['by_priority'].get('MEDIUM', 0)}
- **Normal/Low Priority Items:** {stats['by_priority'].get('NORMAL', 0) + stats['by_priority'].get('LOW', 0)}

### By Channel
- 📧 **Gmail:** {stats['by_channel'].get('Gmail', 0)} messages
- 💼 **LinkedIn:** {stats['by_channel'].get('LinkedIn', 0)} messages
- 💬 **WhatsApp:** {stats['by_channel'].get('WhatsApp', 0)} messages

### By Status
- ✅ **Processed:** {stats['by_status'].get('Processed', 0)}
- ✓ **Approved:** {stats['by_status'].get('Approved', 0)}
- ✗ **Rejected:** {stats['by_status'].get('Rejected', 0)}

---

## 🔴 High Priority Items

"""
        
        if stats['high_priority_messages']:
            for i, msg in enumerate(stats['high_priority_messages'][:10], 1):
                channel_icon = {'EMAIL': '📧', 'LINKEDIN': '💼', 'WHATSAPP': '💬'}.get(msg['channel'], '❓')
                report += f"{i}. {channel_icon} **{msg['from']}** - {msg['subject']} - *{msg['status']}*\n"
        else:
            report += "*No high priority messages this week*\n"
        
        report += f"""

---

## 📊 Channel Breakdown

### Gmail (📧)
- Messages: {stats['by_channel'].get('Gmail', 0)}
- High Priority: {sum(1 for m in stats['high_priority_messages'] if m['channel'] == 'EMAIL')}

### LinkedIn (💼)
- Messages: {stats['by_channel'].get('LinkedIn', 0)}
- High Priority: {sum(1 for m in stats['high_priority_messages'] if m['channel'] == 'LINKEDIN')}

### WhatsApp (💬)
- Messages: {stats['by_channel'].get('WhatsApp', 0)}
- High Priority: {sum(1 for m in stats['high_priority_messages'] if m['channel'] == 'WHATSAPP')}

---

## 📈 Performance Metrics

### Processing Efficiency
- **Total Messages:** {stats['total']}
- **Approval Rate:** {(stats['by_status'].get('Approved', 0) / max(stats['total'], 1) * 100):.1f}%
- **Rejection Rate:** {(stats['by_status'].get('Rejected', 0) / max(stats['total'], 1) * 100):.1f}%

### Priority Distribution
- **HIGH:** {(stats['by_priority'].get('HIGH', 0) / max(stats['total'], 1) * 100):.1f}%
- **MEDIUM:** {(stats['by_priority'].get('MEDIUM', 0) / max(stats['total'], 1) * 100):.1f}%
- **NORMAL/LOW:** {((stats['by_priority'].get('NORMAL', 0) + stats['by_priority'].get('LOW', 0)) / max(stats['total'], 1) * 100):.1f}%

---

## 💡 Recommendations

"""
        
        # Add recommendations based on data
        if stats['by_priority'].get('HIGH', 0) > stats['total'] * 0.3:
            report += "- ⚠️ **High volume of urgent messages** - Consider additional resources\n"
        
        if stats['by_status'].get('Rejected', 0) > stats['total'] * 0.2:
            report += "- 🔍 **High rejection rate** - Review filtering criteria\n"
        
        if stats['by_channel'].get('LinkedIn', 0) > 10:
            report += "- 💼 **Active LinkedIn engagement** - Strong networking activity\n"
        
        report += """

---

*Generated by AI Employee - Gold Tier System*  
*Panaversity AI Employee Hackathon 2026*
"""
        
        return report
    
    def save_report(self, report_content):
        """Save briefing report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"CEO_Briefing_{timestamp}.md"
        filepath = self.briefing_folder / filename
        
        filepath.write_text(report_content)
        print(f"[SAVED] Briefing saved to: {filepath}")
        
        return filepath
    
    def generate(self):
        """Generate complete briefing"""
        print("\n" + "="*60)
        print("CEO WEEKLY BRIEFING GENERATOR")
        print("Gold Tier - AI Employee System")
        print("="*60 + "\n")
        
        print("[ANALYZE] Analyzing messages...")
        stats = self.analyze_messages()
        
        print(f"[STATS] Total messages: {stats['total']}")
        print(f"[STATS] High priority: {stats['by_priority'].get('HIGH', 0)}")
        
        print("\n[GENERATE] Creating briefing report...")
        report = self.generate_markdown_report(stats)
        
        filepath = self.save_report(report)
        
        print("\n" + "="*60)
        print("✅ BRIEFING GENERATED SUCCESSFULLY!")
        print("="*60)
        print(f"Location: {filepath}")
        print("="*60 + "\n")
        
        return filepath

def main():
    vault_path = Path.cwd()
    
    generator = BriefingGenerator(vault_path)
    report_path = generator.generate()
    
    # Display report
    print("\n" + "="*60)
    print("BRIEFING PREVIEW")
    print("="*60 + "\n")
    print(report_path.read_text())

if __name__ == '__main__':
    main()
