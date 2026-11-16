import {readFileSync,writeFileSync,copyFileSync} from 'node:fs';
let html=readFileSync('../../config/monitoring/dashboard.html','utf8');
html=html.replace('<title>Strix Halo</title>','<title>Strix Halo Inference</title>').replace('<h1>Strix Halo</h1>','<h1>Inference</h1>'+readFileSync('frontend/metrics.html','utf8'))
 .replace('<script src="dashboard.js"></script>','<script src="desktop/app/frontend/transport.js"></script><script src="config/monitoring/dashboard.js"></script><script src="desktop/app/frontend/metrics.js"></script>');
writeFileSync('dist/index.html',html);
writeFileSync('dist/dashboard.css',readFileSync('../../config/monitoring/dashboard.css','utf8')+'\n'+readFileSync('frontend/metrics.css','utf8'));
