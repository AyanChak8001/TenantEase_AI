def recommendation(result, late_count, avg_delay, status):
    if status=="OVERDUE": return "Payment is currently overdue. Review the transaction records and contact the tenant to confirm payment status."
    if result["category"]=="Low": return "Tenant has a consistent history of timely payments. Continue standard payment reminders."
    if result["category"]=="Medium": return f"Tenant has experienced occasional payment delays (average {avg_delay:.1f} days). Consider a friendly payment confirmation before the due date."
    return f"Historical payment patterns indicate an elevated likelihood of delayed payment ({late_count} prior late payments). Consider a proactive, respectful follow-up."
