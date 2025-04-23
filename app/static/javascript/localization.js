let localizationData = {};
let defaultLanguage = 'en'; // Язык по умолчанию

// Функция для загрузки файла локализации
async function loadLocalization(filePath) {
    try {
        const response = await fetch(filePath);
        if (!response.ok) {
            throw new Error(`Failed to load localization file: ${response.statusText}`);
        }
        localizationData = await response.json();
    } catch (error) {
        console.error('Error loading localization:', error);
    }
}

function formatString(template, args) {
    return template.replace(/{(\w+)}/g, (match, key) => {
        return key in args ? args[key] : match;
    });
}

// Функция для получения перевода с использованием jmespath
// Объединённая функция для получения перевода и форматирования
function getTranslate(query, placeholders = null, replace = null) {
    const translation = jmespath.search(localizationData, query);

    // Если перевод найден, форматируем строку, если переданы плейсхолдеры
    if (typeof translation === 'string') {
        return placeholders ? translation.replace(/{(\w+)}/g, (match, key) => {
            return key in placeholders ? placeholders[key] : match;
        }) : translation;
    }

    // Если перевод не найден, возвращаем замену или сам путь
    return replace || query;
}

(async () => {
    const html = document.getElementsByTagName('html')[0];
    
    await loadLocalization(`/static/language/${html.lang}.json`);
    console.log(getTranslate('language', 'Err'));
})();