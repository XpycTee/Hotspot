function getDeviceInfo() {
    const info = {};

    // Браузер / система
    const uaData = navigator.userAgentData || {};
    info.userAgent = navigator.userAgent || "";
    info.brands = uaData.brands || [];
    info.mobile = uaData.mobile || false;
    info.platform = uaData.platform || "";
    info.language = navigator.language || "";
    info.languages = navigator.languages || [];

    // Экран / DPI
    info.screen = {
        width: screen.width,
        height: screen.height,
        availWidth: screen.availWidth,
        availHeight: screen.availHeight,
        colorDepth: screen.colorDepth,
        pixelRatio: window.devicePixelRatio || 1,
    };

    // CPU / память
    info.hardware = {
        cores: navigator.hardwareConcurrency || null,
        memory: navigator.deviceMemory || null,
        touchPoints: navigator.maxTouchPoints || 0
    };

    // Локаль/время
    info.time = {
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        offset: new Date().getTimezoneOffset()
    };

    // Наличие cookie
    info.cookieEnabled = navigator.cookieEnabled;

    // Canvas fingerprint
    info.canvas = getCanvasFingerprint();

    // WebGL fingerprint
    info.webgl = getWebGLFingerprint();

    return info;
}


// Canvas fingerprint
function getCanvasFingerprint() {
    try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        ctx.textBaseline = "top";
        ctx.font = "16px 'Arial'";
        ctx.fillText("fingerprint_test_123", 2, 2);
        return canvas.toDataURL();
    } catch {
        return "unsupported";
    }
}

// WebGL fingerprint
function getWebGLFingerprint() {
    try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (!gl) return "no_webgl";

        const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
        return {
            vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : "",
            renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : "",
            maxTexture: gl.getParameter(gl.MAX_TEXTURE_SIZE),
            shadingLang: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
        };
    } catch {
        return "webgl_error";
    }
}
