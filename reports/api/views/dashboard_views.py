# reports/api/views/dashboard_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ...services.dashboard_service import DashboardService

class DashboardKPIsView(APIView):
    """
    Endpoint que retorna los KPIs configurados para el rol del usuario.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        service = DashboardService()
        kpis = service.get_dashboard_kpis(request.user)
        
        # Serializar lista de KPIResult → JSON
        return Response({
            'kpis': [kpi.to_dict() for kpi in kpis]
        })
