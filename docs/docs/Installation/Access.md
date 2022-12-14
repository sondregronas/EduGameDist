# Limiting access
**Please do not expose your instance to the internet, take extra steps to ensure access is limited to your local network.**

## A-record
If you own a domain name, you can create an `A-record` pointing to the IP-address of your local server, which will automatically point to port 80. Be sure to not expose anything to WAN (the internet), only LAN (your local network).

## NginxProxyManager
The recommended way to expose your instance to the internet is to use [NginxProxyManager](https://nginxproxymanager.com/). This will allow you to create URLs for both frontend and backend. Be sure to restrict access to the server to only your local network for the frontend, as games **WILL** be accessible for download from the frontend.

### Access lists
To restrict access to the frontend, you can use the `Access Lists` feature in NginxProxyManager. This will allow you to restrict access to the frontend to only your local network.

> [!INFO]+ RFC1918 Access List
> With the `RFC1918 Access List` in NginxProxyManager you can restrict access to your local network. This will allow you to expose the frontend to the internet, while still restricting access to your local network.
> 
> The IP-addresses used in the `RFC1918 Access List` are:
> - `192.168.0.0/16`
> - `172.16.0.0/12`
> - `10.0.0.0/8`

## Uploading games
Uploading games can either be done via [network shares (Samba/CIFS)](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf#:~:text=To%20share%20a%20file%20or,users%20access%20to%20the%20file.) or by using external drives. You can also use an external SFTP server.

## Remote access (SFTP)
For external connections I recommend configuring a protected SFTP server, for example https://hub.docker.com/r/atmoz/sftp.