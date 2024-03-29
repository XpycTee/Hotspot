<h1 align="center">Hotspot Mikrotik</h1>

<p align="center">
This project provides a backend hotspot web application deployed in a Docker container and a web template for the Mikrotik hotspot.
</p>

<!--
#### Docker
![Downloads](https://img.shields.io/github/downloads/XpycTee/Hotspot/total) ![Contributors](https://img.shields.io/github/contributors/XpycTee/Hotspot?color=dark-green) ![Issues](https://img.shields.io/github/issues/XpycTee/Hotspot) ![License](https://img.shields.io/github/license/XpycTee/Hotspot)
#### Github
![Downloads](https://img.shields.io/github/downloads/XpycTee/Hotspot/total) ![Contributors](https://img.shields.io/github/contributors/XpycTee/Hotspot?color=dark-green) ![Issues](https://img.shields.io/github/issues/XpycTee/Hotspot) ![License](https://img.shields.io/github/license/XpycTee/Hotspot)
-->

## Installation
### Installing the Template in Mikrotik
#### Hotspot HTML Template configure
Download the Mikrotik web template files from the repository in `examples/mikrotik_redirect`.

Edit hostname `hotspot.server.url` in action of redirect form to your server ip or dns name.

> If you want edit template read Mikrotik [Hotspot Customization Documentation](https://help.mikrotik.com/docs/display/ROS/Hotspot+customisation)

For work with backend save required inputs
```html
<!-- This is required inputs don't remove -->
<input type="hidden" name="mac" value="$(mac)">
<input type="hidden" name="link-orig" value="$(link-orig)">
<input type="hidden" name="chap-id" value="$(chap-id)">
<input type="hidden" name="chap-challenge" value="$(chap-challenge)">
<input type="hidden" name="link-login-only" value="$(link-login-only)">
<!-- This is required inputs don't remove -->
```

Upload the template folder `mikrotik_redirect` in your Mikrotik files.

#### Mikrotik Hotspot configure
- Create hotspot profile
   - set HTML Directory to `mikrotik_redirect`
   - set enabled `HTTP CHAP`, `MAC Cookie` and optional `HTTPS`
- Create hotspot users and profiles for employee and guest

##### Configs:
Hotspot profile, using macc-cookie and http-chap is required
```
/ip hotspot profile add html-directory=flash/mikrotik_redirect login-by=mac-cookie,http-chap[,https ssl-certificate=hotspot-certificate] ...
```
Employees, required `name=employee` of user, but user `password` you can edit in configuration of backend.
Param `mac-cookie-timeout` you can set what you want, default for employees `30d`
```
/ip hotspot user profile add name=employees add-mac-cookie=yes mac-cookie-timeout=30d ...
/ip hotspot user add name=employee password=supersecret profile=employees ...
```
Guests, required `name=guest` of user, but `password` you can edit in configuration of backend.
Param `mac-cookie-timeout` you can set what you want, default for guests `1d`
```
/ip hotspot user profile add name=guests add-mac-cookie=yes mac-cookie-timeout=1d ...
/ip hotspot user add name=guest password=secret profile=guests ...
```
> For more detail read Mikrotik [Hotspot User Documentation](https://help.mikrotik.com/docs/display/ROS/User)
### Installing the Backend in Docker
Pull the Docker image from DockerHub: 
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
