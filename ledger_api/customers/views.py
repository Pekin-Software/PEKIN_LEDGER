from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import viewsets, status
from .models import Client, Domain, User
from .serializers import ClientSerializer, DomainSerializer, UserSerializer
from django.contrib.auth import authenticate
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        # Handle user creation
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User and Client (Tenant) created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def index(request):
    return(HttpResponse("<h1>Public</h1>"))

class LoginViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        print(f"Trying to authenticate user: {username}")  # Debugging line
        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            print(f"Authentication failed for {username}")  # Debugging line
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Fetch the tenant domain
        try:
            tenant_domain = Domain.objects.get(tenant=user.domain).domain
        except Domain.DoesNotExist:
            print(f"Domain for tenant {user.domain} not found")  # Debugging line
            return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

        # return Response({
        #     "access_token": access_token,
        #     "refresh_token": str(refresh),
        #     "redirect_url": f"http://{tenant_domain}:8000/",
        # }, status=status.HTTP_200_OK)
        return render(request, 'redirect_page.html', {
            'redirect_url': f'http://{tenant_domain}:8000/',  # Pass the URL to the template
            'access_token': access_token,
            'refresh_token': str(refresh)
        })
        
        
        
        
