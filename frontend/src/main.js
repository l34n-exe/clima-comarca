import { mount } from 'svelte';
import 'layerchart/core.css';
import '@fontsource-variable/bricolage-grotesque/standard.css';
import './app.css';
import App from './App.svelte';

mount(App, { target: document.getElementById('app') });
