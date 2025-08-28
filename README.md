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
1. Download the Mikrotik web template files from the repository in `examples/mikrotik_redirect`.
2. Edit the hostname `hotspot.server.url` in the action of the redirect form to your server IP or DNS name.

> If you want to edit the template, refer to the Mikrotik [Hotspot Customization Documentation](https://help.mikrotik.com/docs/display/ROS/Hotspot+customisation).

3. For working with the backend, save the required inputs:
```html
<!-- These are required inputs, do not remove -->
<input type="hidden" name="mac" value="$(mac)">
<input type="hidden" name="link-orig" value="$(link-orig)">
<input type="hidden" name="chap-id" value="$(chap-id)">
<input type="hidden" name="chap-challenge" value="$(chap-challenge)">
<input type="hidden" name="link-login-only" value="$(link-login-only)">
<!-- These are required inputs, do not remove -->
```

4. Upload the template folder mikrotik_redirect to your Mikrotik files.

### Mikrotik Hotspot Configuration
- Create a hotspot profile:
   - Set HTML Directory to `mikrotik_redirect`
   - Enable `HTTP CHAP`, `MAC Cookie` and optionally `HTTPS`
- Create hotspot users and profiles for employees and guests.

##### Configurations:
1. Hotspot profile, using macc-cookie and http-chap is required:
```
/ip hotspot profile add html-directory=flash/mikrotik_redirect login-by=mac-cookie,http-chap[,https ssl-certificate=hotspot-certificate] ...
```
2. Employees, with required `name=employee` of the user, but you can edit the user `password` in the backend configuration. The parameter `mac-cookie-timeout` can be set as needed, default for employees is `30d`:
```
/ip hotspot user profile add name=employees add-mac-cookie=yes mac-cookie-timeout=30d ...
/ip hotspot user add name=employee password=supersecret profile=employees ...
```
3. Guests, with required `name=guest` of the user, but you can edit the `password` in the backend configuration. The parameter `mac-cookie-timeout` can be set as needed, default for guests is `1d`:
```
/ip hotspot user profile add name=guests add-mac-cookie=yes mac-cookie-timeout=1d ...
/ip hotspot user add name=guest password=secret profile=guests ...
```
> For more detail read Mikrotik [Hotspot User Documentation](https://help.mikrotik.com/docs/display/ROS/User)

### Installing the Backend
#### Prepare PostgresSQL
```bash
docker run -d \
    --name hotspot-db \
    -e POSTGRES_DB=hotspot \
    -e POSTGRES_USER=hotspot \
    -e POSTGRES_PASSWORD=OmegaSuperSecret \
    postgres
```
> This command runs a PostgresSQL container named `hotspot-db` with specific environment variables for database setup.
#### Create Hotspot container
Start a hotspot backend web-interface container as follows:
```bash
docker run -d \
    --name hotspot-app \
    -v /path/to/config:/hotspot/config \
    xpyctee/hotspot-mikrotik:latest-postgres
```
> This command starts a hotspot backend container named `hotspot-app` with a volume mounted for configuration.
### Environment Variables
| Variable                   | Description                                               | Example Value                                            |
|----------------------------|-----------------------------------------------------------|----------------------------------------------------------|
| `DEBUG`                    | Enables or disables debug mode.                           | `true`                                                   |
| `HOTSPOT_COMPANY_NAME`     | The name of the company displayed in the application.     | `"No-name LTD"`                                          |
| `HOTSPOT_LANGUAGE`         | Language for the application.                             | `"en"`                                                   |
| `HOTSPOT_DB_URL`           | Database connection URL using SQLAlchemy format.          | `"postgresql://hotspot:password@127.0.0.1:5432/hotspot"` |
| `HOTSPOT_ADMIN_USERNAME`   | Username for the admin user.                              | `"admin"`                                                |
| `HOTSPOT_ADMIN_PASSWORD`   | Password for the admin user.                              | `"admin"`                                                |
| `HOTSPOT_GUEST_PASSWORD`   | Default password for guest users.                         | `"secret"`                                               |
| `HOTSPOT_GUEST_DELAY`      | Duration for guest user access.                           | `"24h"`                                                  |
| `HOTSPOT_EMPLOYEE_PASSWORD`| Default password for employee users.                      | `"supersecret"`                                          |
| `HOTSPOT_EMPLOYEE_DELAY`   | Duration for employee user access.                        | `"30d"`                                                  |
| `HOTSPOT_SENDER_TYPE`      | Type of SMS sender (e.g., `mikrotik`, `huawei`, `smsru`). | `"mikrotik"`                                             |
| `HOTSPOT_SENDER_URL`       | URL for the SMS sender API.                               | `"https://admin:@182.168.88.1/"`                         |
| `FLASK_SECRET_KEY`         | Secret key for Flask application security.                | `"your-secret-key"`                                      |
| `CACHE_URL`                | URL for the cache server (e.g., Memcached or Redis).      | `"memcached://localhost:11211"`                          |
| `CACHE_SIZE`               | Cache size in megabytes.                                  | `"1024"`                                                 |
| `GUNICORN_WORKERS`         | Number of Gunicorn workers for handling requests.         | `"4"`                                                    |
| `GUNICORN_LOG_LEVEL`       | Log level for Gunicorn (e.g., `debug`, `info`, `warning`).| `"info"`                                                 |
| `GUNICORN_ADDR`            | Address for Gunicorn to bind to.                          | `"[::]"`                                              |
| `GUNICORN_PORT`            | Port for Gunicorn to listen on.                           | `"8080"`                                                 |

### Config Examples
Default we have some sms senders:
1. Mikrotik  - Send SMS use Mikrotik RESTful API (Required ROS7).
2. HUAWEI Modem - Send SMS use HUAWEI Modem's API.
3. sms.ru - Russian service for SMS sending.
> Maybe expand in the future. Examples of APIs see in `examples/config`

#### Settings.yaml
For example use mikrotik api configuration file saved in: `config/settings.yaml`:
```yaml
settings:
  company_name: No-name LTD
  language: en
  db_url: postgresql://hotspot:OmegaSuperSecret@127.0.0.1:5432/hotspot  # OPTIONAL. Url for connect database use SQLAlchemy URL, by default used sqlite db, file created after start in config directory
  cache_url: memcached://localhost:11211 # OPTIONAL. Url for connect cache use URL, by default used in-memory cache
  admin:
    user:
      username: admin
      password: admin  # Default password is admin
  sender:
    type: mikrotik
    url: https://admin:@182.168.88.1/  # Url for REST api of mikrotik RoS Version >=7.9
  hotspot_users:
    guest:
      password: secret # Default password for guests used in mikrotik /ip hotspot user add password=secret ...
      delay: 24h # Hours. You can use suffixes such as: w, d, m, s. Without a suffix, the default is hours.
    employee:
      password: supersecret # Default password for employees used in mikrotik /ip hotspot user add password=supersecret ...
      delay: 30d # Days. You can use suffixes such as: w, d, m, s. Without a suffix, the default is hours.
```
> This YAML configuration file provides settings for the Mikrotik API, company details, and user configurations.

## License

This project is licensed under the [MIT License](./LICENSE).

## Authors

- [@xpyctee](https://www.github.com/xpyctee)
