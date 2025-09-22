from celery import shared_task

@shared_task
def aggregate_daily_metrics():
    """Daily aggregation task (runs at midnight)"""
    # TODO: Implement actual daily logic
    return "Ran daily aggregation"

@shared_task
def aggregate_weekly_metrics():
    """Weekly aggregation task (runs Sunday midnight)"""
    return "Ran weekly aggregation"

@shared_task
def aggregate_monthly_metrics():
    """Monthly aggregation task (runs 1st of month)"""
    return "Ran monthly aggregation"
