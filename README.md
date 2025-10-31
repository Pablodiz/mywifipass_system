# MyWifiPass System

The comprehensive web application component of MyWifiPass for managing Wi-Fi clients and networks with EAP-TLS authentication.

## Overview

MyWifiPass System is the server-side component that provides a web-based management interface for implementing EAP-TLS authentication in enterprise wireless networks. It automates the complex processes of certificate management, RADIUS server configuration, and network deployment.

## Features

- **User Management**: Create and manage Wi-Fi users with automatic certificate generation
- **Network Configuration**: Define and configure multiple wireless networks with EAP-TLS settings
- **RADIUS Integration**: Automatically configures FreeRADIUS server for each managed network
- **Certificate Management**: Full PKI lifecycle including generation, distribution, and revocation
- **Email Notifications**: Automated certificate delivery to users
- **QR Code Generation**: Create QR codes for easy Android app configuration
- **OpenWISP Integration**: Simplified setup and basic configuration of OpenWISP for access point management
- **RESTful API**: Integration capabilities with third-party systems

## Architecture

The system is built using a containerized microservices architecture:

- **Web Application**: Django-based management interface
- **RADIUS Server**: FreeRADIUS with EAP-TLS configuration
- **Database**: PostgreSQL for data persistence
- **Certificate Authority**: Internal PKI for certificate management
- **OpenVPN Server**: Secure remote access gateway

## Quick Start

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/Pablodiz/mywifipass_system.git
   cd mywifipass_system
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy with Docker**. Use `mywifipass` for deploying MyWifiPass system or `all` for including OpenWISP integrations:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh {mywifipass|all}
   ```

## Configuration

Edit the `.env` file to configure:
- Database credentials
- Email settings for certificate delivery
- Domain and SSL settings
- RADIUS server configuration
- OpenWISP integration settings

## Wi-Fi Pass Generation

The system generates "Wi-Fi passes", which let Wi-Fi clients download the credentials needed for connecting to the networks. They include:
- Network SSID
- Metadata for contextualizing the network
- URLs for obtaining the client certificates for EAP-TLS authentication and CA certificates for server validation

## OpenWISP

MyWifiPass includes optional integration with OpenWISP for access point management. When deployed with the `all` option, the system provides:

- **Automated Setup**: Simplified deployment of OpenWISP controller and dashboard
- **Basic Configuration**: Pre-configured template for EAP-TLS configuration
- **Access Point Auto-Configuration**: Generates setup scripts for easy AP deployment

The OpenWISP integration is designed to get you started quickly with access point management, though advanced OpenWISP features may require additional manual configuration.

### Access Point Setup

When deploying with the `all` option, MyWifiPass automatically generates a configuration script (`configure_openwisp.sh`) that simplifies access point integration:

1. **Copy the script** to your target access point device
2. **Execute the script** on the access point (requires internet connectivity)
3. **Automatic configuration** of OpenWISP agent and network settings

**Requirements**: Target access points must have internet access during the configuration process.

## Related Projects

- **[MyWifiPass Android](https://github.com/Pablodiz/mywifipass_android)**: Android app for automated network configuration
- **[Main Project Repository](https://github.com/Pablodiz/TFG_proyecto)**: Complete project documentation and overview

## User manual

Refer to [the user manual](./user_manual.md) for help managing the system. 

## License

This project is part of the MyWifiPass ecosystem designed to simplify enterprise wireless security deployment.