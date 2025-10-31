# USER MANUAL

As an administrator of MyWifiPass System, you will manage two main elements: Wi-Fi Clients and Wi-Fi Networks.

## Wi-Fi Networks

These represent deployed Wi-Fi networks that use the EAP-TLS protocol. You can configure their SSID as well as metadata to identify them. When you create/update one, there are 3 key checkboxes:

- **Is enabled in RADIUS**: Whether the network configuration should be added to the authentication server or not.
- **Is visible in web**: Whether the network is shown on the main web interface for users to see.
- **Is registration open**: Whether users can register themselves for this network or not.

## Wi-Fi Clients

These are the end users of your system. For each client, you can manage the following options:

- **Has downloaded pass**: Indicates whether the user has downloaded their Wi-Fi pass or not. If activated, they won't be able to download it again.
- **Has attended**: Indicates whether the user has accessed the network or not. If activated, they won't be able to request new certificates.
- **Revoke certificate**: This button revokes user certificates, denying access to the network.

### Managing Wi-Fi Clients

You can create new Wi-Fi clients by providing their basic information (name, email, ID document). You may also import CSV files or allow them to register themselves. Once created, the system will:
1. Generate unique certificates for the user
2. Send an email with their Wi-Fi pass download link
3. Allow you to track their connection status and manage their access