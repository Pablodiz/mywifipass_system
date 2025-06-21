#!/bin/bash
set -e  # Exit on any error

source ./.env

chmod +x ./deploy_scripts/*.sh

# Función para mostrar ayuda
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all              Deploy all services (OpenWISP + MyWifiPass)"
    echo "  openwisp         Download OpenWISP repository to configure it (with option 'all', its automated)" 
    echo "  mywifipass       Deploy only MyWifiPass services"
    echo "  stop-all         Stop all services"
    echo "  stop-mywifipass  Stop MyWifiPass services"
    echo "  help             Show this help message"
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
        git checkout 7603dc2723f064cda35d0693b9813c2591cb6d1a # Last checked working commit
        cd .. 
    fi
}

# Create mywifipass url 
if [ "$SSL" = "True" ] || [ "$SSL" = "true" ]; then
    PROTOCOL="https"
else
    PROTOCOL="http"
fi

# Function for configuring mywifipass + openwisp 
setup_all() {
    # if [ ! -f ./deploy_scripts/done ]; then
        touch ./deploy_scripts/done
        echo "Configuring OpenVPN for RADIUS server..." 
        ./deploy_scripts/create_radius_openvpn_config.sh
        echo "Creating a template for EAP-TLS in OpenWISP Dashboard..."
        docker cp ./deploy_scripts/create_tls_template.py openwisp-dashboard:/opt/openwisp
        docker exec -it -e RADIUS_PORT=1812 -e RADIUS_SERVER=10.8.0.10 -e RADIUS_SECRET=$(cat ./our_radius/RADIUS_SECRET/secret.txt) openwisp-dashboard python3 create_tls_template.py
    # fi
}

# Function for deploying all services
deploy_all() {
    echo "Starting deployment of all services..."
    download_openwisp
    cp .env docker-openwisp/.env
    docker compose -f complete-docker-compose.yaml -f docker-compose.override.yaml up -d --pull always
    setup_all
    echo "Generating script to configure openwisp in access points..."
    ./deploy_scripts/generate_openwrt_openwisp_config.sh
    echo "✅ All services deployed successfully!"
    echo "OpenWISP Dashboard should be available at: https://${DASHBOARD_DOMAIN}"
    echo "MyWifiPass should be available at: ${PROTOCOL}://localhost:${WEBAPP_PORT:-10000}"}
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
    "stop-all")
        echo "Stopping all services..."
        docker compose -f complete-docker-compose.yaml -f docker-compose.override.yaml down
        echo "✅ All services stopped successfully!"
        ;;
    "stop-mywifipass")
        echo "Stopping MyWifiPass services..."
        docker compose -f docker-compose.yaml down
        echo "✅ MyWifiPass services stopped successfully!"
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