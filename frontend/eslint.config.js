import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
    {ignores: ['dist', 'coverage', '**/*.test.js', '**/*.test.jsx', '**/*.spec.js', '**/*.spec.jsx',
            'e2e/**', 'src/test/**', '**/__tests__/**', 'vitest.config.js', 'playwright.config.js',
            'setup-tests.sh', 'playwright-report/**']},
    // Separate config for vite.config.js with Node.js globals
    {
        files: ['vite.config.js'],
        languageOptions: {
            ecmaVersion: 2020,
            globals: globals.node,
            parserOptions: {
                ecmaVersion: 'latest',
                sourceType: 'module',
            },
        },
    },
    {
        files: ['**/*.{js,jsx}'],
        languageOptions: {
            ecmaVersion: 2020,
            globals: globals.browser,
            parserOptions: {
                ecmaVersion: 'latest',
                ecmaFeatures: {jsx: true},
                sourceType: 'module',
            },
        },
        settings: {react: {version: '18.3'}},
        plugins: {
            react,
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
        },
        rules: {
            ...js.configs.recommended.rules,
            ...react.configs.recommended.rules,
            ...react.configs['jsx-runtime'].rules,
            ...reactHooks.configs.recommended.rules,
            'no-unused-vars': 'off',
            'react/prop-types': 'off',
            'react/jsx-no-target-blank': 'off',
            'react-hooks/exhaustive-deps': 'off',
            'react/no-unescaped-entities': 'off',
            'react/display-name': 'off',
            'no-empty-pattern': 'off',
            'no-prototype-builtins': 'off',
            'react-refresh/only-export-components': 'off',
            // Relax React Compiler-driven hook rules for incremental adoption.
            'react-hooks/set-state-in-effect': 'off',
            'react-hooks/refs': 'off',
            'react-hooks/purity': 'off',
            'react-hooks/immutability': 'off',
            'react-hooks/preserve-manual-memoization': 'off',
            'react-hooks/static-components': 'off',
        },
    },
]
