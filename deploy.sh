#!/bin/bash
set -e  # Exit on any error

chmod +x ./deploy_scripts/*.sh

# Función para mostrar ayuda
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all         Deploy all services (OpenWISP + MyWifiPass)"
    echo "  openwisp    Download OpenWISP repository to configure it (with option 'all', its automated)" 
    echo "  mywifipass  Deploy only MyWifiPass services"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all"
    echo "  $0 mywifipass"
}

download_openwisp(){
    if [ ! -d "docker-openwisp" ]; then
        echo "Cloning OpenWISP repository..."
        git clone https://github.com/openwisp/docker-openwisp.git docker-openwisp
        cd docker-openwisp
        git checkout 7603dc2723f064cda35d0693b9813c2591cb6d1a # Last checked commit
        make pull
        cd .. 
    fi
}

# Create mywifipass url 
if [ "$SSL" = "True" ] || [ "$SSL" = "true" ]; then
    PROTOCOL="https"
else
    PROTOCOL="http"
fi

# Function for deploying mywifipass + openwisp 
deploy_all() {
    echo "Deploying all services..."
    download_openwisp
    echo "Building and starting all services..."
    cp .env docker-openwisp/.env
    docker compose -f complete-docker-compose.yaml -f docker-compose.override.yaml up -d --build
    echo "Configuring OpenVPN for RADIUS server..." 
    ./deploy_scripts/create_radius_openvpn_config.sh
    echo "Creating a template for EAP-TLS in OpenWISP Dashboard..."
    docker cp ./deploy_scripts/create_tls_template.py openwisp-dashboard:/opt/openwisp
    docker exec -it -e RADIUS_PORT=1812 -e RADIUS_SERVER=10.8.0.10 -e RADIUS_SECRET=$(cat ./our_radius/RADIUS_SECRET/secret.txt) openwisp-dashboard python3 create_tls_template.py
    echo "Generating script to configure openwisp in access points..."
    ./deploy_scripts/create_openwisp_config.sh
    echo "✅ All services deployed successfully!"
    echo "OpenWISP Dashboard should be available at: ${DASHBOARD_DOMAIN}"
    echo "MyWifiPass should be available at: ${PROTOCOL}://localhost:${WEBAPP_PORT:-10000}"
}

# Function for deploying only MyWifiPass
deploy_mywifipass() {
    echo "Deploying MyWifiPass services..."    
    echo "Building and starting MyWifiPass services..."
    docker compose -f docker-compose.yaml up -d --build    
    echo "✅ MyWifiPass services deployed successfully!"
    echo "MyWifiPass should be available at: ${PROTOCOL}://localhost:${WEBAPP_PORT:-10000}"
}



# Verificar que se pasó un argumento
if [ $# -eq 0 ]; then
    echo "Error: No arguments provided"
    show_help
    exit 1
fi

# Procesar el argumento
case "$1" in
    "all")
        deploy_all
        ;;
    "mywifipass")
        deploy_mywifipass
        ;;
    "openwisp")
        download_openwisp
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Error: Invalid argument '$1'"
        show_help
        exit 1
        ;;
esac

echo ""
echo "To check status: docker compose ps"
echo "To view logs: docker compose logs -f [service_name]"