(function () {
    "use strict";

    function gruposMilharValidos(parte, separador) {
        const grupos = String(parte).split(separador);
        if (!grupos.length || !/^\d{1,3}$/.test(grupos[0])) return false;
        return grupos.slice(1).every(g => /^\d{3}$/.test(g));
    }

    function parse(value) {
        if (value === null || value === undefined) return 0;

        const original = String(value).trim();
        if (!original) return 0;

        let raw = original
            .replace(/R\$\s?/gi, '')
            .replace(/US\$\s?/gi, '')
            .replace(/€\s?/g, '')
            .replace(/\u00a0/g, ' ')
            .replace(/[^\d.,-]/g, '')
            .trim();

        if (!raw) return null;
        if (raw.includes('-')) return null;

        const hasDot = raw.includes('.');
        const hasComma = raw.includes(',');
        let normalizado = '';

        if (hasDot && hasComma) {
            const lastDot = raw.lastIndexOf('.');
            const lastComma = raw.lastIndexOf(',');
            const decimalEhVirgula = lastComma > lastDot;
            const sepMilhar = decimalEhVirgula ? '.' : ',';
            const sepDecimal = decimalEhVirgula ? ',' : '.';
            const intPart = raw.slice(0, raw.lastIndexOf(sepDecimal));
            const decPart = raw.slice(raw.lastIndexOf(sepDecimal) + 1);

            if (!/^\d{1,2}$/.test(decPart)) return null;
            if (intPart.includes(sepMilhar) && !gruposMilharValidos(intPart, sepMilhar)) return null;
            if (!/^\d+$/.test(intPart.replaceAll(sepMilhar, ''))) return null;
            normalizado = `${intPart.replaceAll(sepMilhar, '')}.${decPart}`;
        } else if (hasComma) {
            const partes = raw.split(',');
            const ultima = partes[partes.length - 1];

            if (partes.length > 2) {
                if (/^\d{1,2}$/.test(ultima) && gruposMilharValidos(partes.slice(0, -1).join(','), ',')) {
                    normalizado = `${partes.slice(0, -1).join('')}.${ultima}`;
                } else if (/^\d{3}$/.test(ultima) && gruposMilharValidos(raw, ',')) {
                    normalizado = partes.join('');
                } else {
                    return null;
                }
            } else if (/^\d{1,2}$/.test(ultima)) {
                normalizado = `${partes[0] || '0'}.${ultima}`;
            } else if (/^\d{3}$/.test(ultima)) {
                normalizado = partes.join('');
            } else {
                return null;
            }
            if (!normalizado || !/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;
        } else if (hasDot) {
            const partes = raw.split('.');
            const ultima = partes[partes.length - 1];

            if (partes.length > 2) {
                if (/^\d{1,2}$/.test(ultima) && gruposMilharValidos(partes.slice(0, -1).join('.'), '.')) {
                    normalizado = `${partes.slice(0, -1).join('')}.${ultima}`;
                } else if (/^\d{3}$/.test(ultima) && gruposMilharValidos(raw, '.')) {
                    normalizado = partes.join('');
                } else {
                    return null;
                }
            } else if (/^\d{1,2}$/.test(ultima)) {
                normalizado = `${partes[0] || '0'}.${ultima}`;
            } else if (/^\d{3}$/.test(ultima)) {
                normalizado = partes.join('');
            } else {
                return null;
            }
            if (!normalizado || !/^\d+(\.\d{1,2})?$/.test(normalizado)) return null;
        } else {
            if (!/^\d+$/.test(raw)) return null;
            normalizado = raw;
        }

        const numero = Number(normalizado);
        return Number.isFinite(numero) ? numero : null;
    }

    function formatCurrency(value, currency) {
        if (value === null || value === undefined || value === '') return '';
        const numero = Number(value);
        if (!Number.isFinite(numero)) return '';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: currency || 'BRL'
        }).format(numero);
    }

    function formatInteger(value) {
        if (value === null || value === undefined || value === '') return '';
        const numero = Number(value);
        if (!Number.isFinite(numero)) return '';
        return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(Math.round(numero));
    }

    function formatInput(input, currency) {
        if (!input) return;
        const numero = parse(input.value);
        if (numero === null || numero < 0) return;
        input.value = formatCurrency(numero, currency || 'BRL');
    }

    function formatIntegerInput(input) {
        if (!input) return;
        const numero = parse(input.value);
        if (numero === null || numero < 0) return;
        input.value = formatInteger(numero);
    }

    window.ValorMonetario = {
        parse,
        formatCurrency,
        formatInteger,
        formatInput,
        formatIntegerInput
    };
})();
