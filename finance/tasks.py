from celery import shared_task

class AnalyticsAggregationTasks:
    @staticmethod
    def aggregate_daily_metrics():
        # Your aggregation logic here
        pass

    @staticmethod
    def aggregate_weekly_metrics():
        pass

    @staticmethod
    def aggregate_monthly_metrics():
        pass

@shared_task
def aggregate_daily_metrics():
    return AnalyticsAggregationTasks.aggregate_daily_metrics()

@shared_task
def aggregate_weekly_metrics():
    return AnalyticsAggregationTasks.aggregate_weekly_metrics()

@shared_task
def aggregate_monthly_metrics():
    return AnalyticsAggregationTasks.aggregate_monthly_metrics()
