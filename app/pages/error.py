from flask import Blueprint, render_template

error_bp = Blueprint('errors', __name__)


@error_bp.app_errorhandler(404)
def error_404(err):
    return render_template(
        'error.html',
        code=404,
        title="Страница не найдена",
        description='К сожалению, запрашиваемая вами страница не может быть найдена. Возможно, она была перемещена, удалена или никогда не существовала.'), 404


@error_bp.app_errorhandler(403)
def error_403(err):
    return render_template(
        'error.html',
        code=403,
        title="Доступ запрещен",
        description="У вас нет разрешения на доступ к этой странице. Пожалуйста, проверьте свои учетные данные или обратитесь к администратору сайта."), 403


@error_bp.app_errorhandler(500)
def error_500(err):
    print(err)
    return render_template(
        'error.html',
        code=500,
        title="Внутренняя ошибка сервера",
        description="Что-то пошло не так, и сервер не смог выполнить ваш запрос. Мы уже работаем над устранением проблемы. Попробуйте обновить страницу или вернуться позже."), 500


@error_bp.app_errorhandler(401)
def error_401(err):
    print(err)
    return render_template(
        'error.html',
        code=401,
        title="Неавторизованный доступ",
        description="Для просмотра запрашиваемой страницы требуется авторизация. Пожалуйста, войдите в свой аккаунт или зарегистрируйтесь."), 401


@error_bp.app_errorhandler(503)
def error_503(err):
    print(err)
    return render_template(
        'error.html',
        code=503,
        title="Сервис недоступен",
        description="В данный момент сервер не может обработать ваш запрос из-за временных трудностей. Пожалуйста, попробуйте повторить запрос позже."), 503


@error_bp.app_errorhandler(400)
def error_400(err):
    print(err)
    return render_template(
        'error.html',
        code=400,
        title="Неверный запрос",
        description="Ваш запрос не может быть обработан из-за ошибки в переданных данных. Пожалуйста, проверьте свои параметры запроса и повторите попытку."), 400


@error_bp.app_errorhandler(429)
def error_429(err):
    print(err)
    return render_template(
        'error.html',
        code=429,
        title="Слишком много запросов",
        description="Вы отправили слишком много запросов за короткое время. Пожалуйста, подождите некоторое время и повторите ваш запрос."), 429


@error_bp.app_errorhandler(405)
def error_405(err):
    print(err)
    return render_template(
        'error.html',
        code=405,
        title="Метод не разрешен",
        description="Метод не разрешен для запрашиваемого URL."), 405


@error_bp.app_errorhandler(502)
def error_502(err):
    print(err)
    return render_template(
        'error.html',
        code=502,
        title="Плохой шлюз",
        description="Возникла проблема с шлюзом или прокси-сервером, который передает ваш запрос. Попробуйте повторить запрос или обратитесь к администратору системы."), 500
