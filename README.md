# Hotspot Mikrotik

This project provides a backend hotspot web application deployed in a Docker container and a web template for the Mikrotik hotspot.

## Installation

### Installing the Template in Mikrotik
- Download the Mikrotik web template files from the repository in `examples/mikrotik_redirect`.
- Upload the template files `mikrotik_redirect` to your Mikrotik files.
- Create hotspot profile
   - set HTML Directory to mikrotik_redirect
   - set enabled HTTP CHAP, MAC Cookie and optional HTTPS
- Create hotspot users and profiles for employee and guest

#### Config:

Hotspot profile
```
/ip hotspot profile add html-directory=flash/mikrotik_redirect login-by=mac-cookie,http-chap[,https ssl-certificate=hotspot-certificate] ...
```
employees
```
/ip hotspot user profile add name=employees add-mac-cookie=yes mac-cookie-timeout=30d ...
/ip hotspot user add name=employee password=supersecret profile=employees ...
```
guests
```
/ip hotspot user profile add name=guests add-mac-cookie=yes mac-cookie-timeout=1d ...
/ip hotspot user add name=guest password=secret profile=guests ...
```

### Installing the Backend in Docker
- Pull the Docker image from DockerHub: 
```bash
docker pull hotspot-mikrotik:latest
```
- Run the Docker container: 
```bash
docker run -d hotspot-mikrotik:latest
```

### Environment Variables for the Backend
- `ENV_NAME`: Example of env var

## License

This project is licensed under the [Apache](./LICENSE).

## Authors

- [@xpyctee](https://www.github.com/xpyctee)
