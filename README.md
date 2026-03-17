# MyWifiPass System

The comprehensive web application component of MyWifiPass for managing Wi-Fi clients and networks with EAP-TLS authentication. 

## Overview

MyWifiPass System is the server-side component that provides a web-based management interface for implementing EAP-TLS authentication in enterprise wireless networks. It automates the complex processes of certificate management, RADIUS server configuration, and network deployment. 

The core certificate generation engine and database models originated as a simplified fork of the open-source library [django-x509](https://github.com/openwisp/django-x509). It has been extensively modified and adapted specifically for this project's requirements.

## Features

- **User Management**: Create and manage Wi-Fi users with automatic certificate generation
- **Network Configuration**: Define and configure multiple wireless networks with EAP-TLS settings
- **RADIUS Integration**: Automatically configures FreeRADIUS server for each managed network
- **Certificate Management**: Full PKI lifecycle including generation, distribution, and revocation
- **Email Notifications**: Automated certificate delivery to users
- **QR Code Generation**: Create QR codes for easy Android app configuration
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

3. **Deploy with Docker**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   # Or alternatively:
   # docker compose up -d
   ```

## Configuration

Edit the `.env` file to configure:
- Database credentials
- Email settings for certificate delivery
- Domain and SSL settings
- RADIUS server configuration

## Wi-Fi Pass Generation

The system generates "Wi-Fi passes", which let Wi-Fi clients download the credentials needed for connecting to the networks. They include:                      
- Network SSID
- Metadata for contextualizing the network
- URLs for obtaining the client certificates for EAP-TLS authentication and CA certificates for server validation

## Related Projects

- **[MyWifiPass Android](https://github.com/Pablodiz/mywifipass_android)**: Android app for automated network configuration
- **[Main Project Repository](https://github.com/Pablodiz/TFG_proyecto)**: Complete project documentation and overview

## User manual

Refer to [the user manual](./user_manual.md) for help managing the system. 

## License

This project is part of the MyWifiPass ecosystem designed to simplify enterprise wireless security deployment. It follows the **BSD 3-Clause License**, retaining the original copyright notices from the `django-x509` community (`Copyright (c) 2015, Federico Capoano / OpenWISP`), alongside the updated copyright for the MyWifiPass logic and infrastructure (`Copyright (c) 2025, Pablo Diz de la Cruz`).

---
*Note: In version 1.0, as part of the Degree Thesis, a small integration with OpenWISP was included. However, this has been removed and is no longer maintained in current versions to streamline the standalone architecture.*
