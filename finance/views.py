from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FinancialAnalytics, RevenueTracking, CourseRevenue, PaymentTransaction
from .serializers import FinancialAnalyticsSerializer, RevenueTrackingSerializer, CourseRevenueSerializer, PaymentTransactionSerializer
from rest_framework import viewsets

class DashboardOverviewAPIView(APIView):
    def get(self, request):
        overview = FinancialAnalytics.objects.last()
        if overview:
            serializer = FinancialAnalyticsSerializer(overview)
            return Response(serializer.data)
        return Response({"detail": "No data found"}, status=status.HTTP_404_NOT_FOUND)

class DashboardHighlightsAPIView(APIView):
    def get(self, request):
        # Example: dummy highlights — adjust based on actual logic
        return Response({
            "recent_transactions": 5,
            "new_courses": 2,
            "top_performing_course": "Research Innovation"
        })

class DashboardTasksAPIView(APIView):
    def get(self, request):
        # Example: dummy admin tasks — adjust based on your app
        return Response({
            "pending_payouts": 3,
            "unapproved_courses": 1,
            "flagged_transactions": 0
        })
    

class RevenueAnalyticsAPIView(APIView):
    def get(self, request):
        data = RevenueTracking.objects.all()
        serializer = RevenueTrackingSerializer(data, many=True)
        return Response(serializer.data)

class ExpenseAnalyticsAPIView(APIView):
    def get(self, request):
        data = RevenueTracking.objects.all()
        # Filter to show only expenses if needed
        serializer = RevenueTrackingSerializer(data, many=True)
        return Response(serializer.data)

class CourseRevenueAPIView(APIView):
    def get(self, request):
        data = CourseRevenue.objects.all()
        serializer = CourseRevenueSerializer(data, many=True)
        return Response(serializer.data)



class PaymentTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
