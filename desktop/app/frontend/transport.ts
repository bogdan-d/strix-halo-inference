// This is the only native/browser boundary; the shared chart and control code stays type-checked.
(() => {
    const core = window.__TAURI__!.core;
    type NativeAction = {kind:"start";engine:string;profile:string;npu:boolean} | {kind:"stop"|"clear";engine:string} | {kind:"monitoring";start:boolean};
    let serial = 0;
    // Serialize stream replacement so an older async start cannot replace a newer viewer.
    let previous: Promise<void> = Promise.resolve();
    window.inferenceTransport = {
        state: () => core.invoke<State>('dashboard_state'),
        async action(path) {
            const parts = path.split('/').slice(1);
            let action: NativeAction;
            if (parts[0] === 'monitoring' && parts.length === 2 && ['start','stop'].includes(parts[1])) {
                action = {kind:'monitoring',start:parts[1] === 'start'};
            } else if (parts[0] === 'cache' && parts[2] === 'clear' && parts.length === 3) {
                action = {kind:'clear',engine:parts[1]};
            } else if (parts[0] === 'engine' && parts[2] === 'stop' && parts.length === 3) {
                action = {kind:'stop',engine:parts[1]};
            } else if (parts[0] === 'engine' && ['start','start-npu'].includes(parts[2]) && parts.length === 4) {
                action = {kind:'start',engine:parts[1],profile:parts[3],npu:parts[2] === 'start-npu'};
            } else throw new Error('Unknown dashboard action');
            const result = await core.invoke<{status:number;text:string}>('dashboard_action',{action});
            return new Response(result.text,{status:result.status});
        },
        async logs(source,signal,write) {
            const id = ++serial;
            const start = previous.catch(() => {}).then(async () => {
                if (signal.aborted) return;
                const decoder = new TextDecoder();
                const channel = new core.Channel<{bytes:number[];done:boolean}>();
                channel.onmessage = ({bytes,done}) => {
                    if (signal.aborted) return;
                    write(decoder.decode(new Uint8Array(bytes),{stream:!done}));
                    if (done) write('\n[log ended]\n');
                };
                await core.invoke('logs_start',{source,id,channel});
                const stop = () => {void core.invoke('logs_stop',{id}).catch(console.error);};
                signal.addEventListener('abort',stop,{once:true});
                if (signal.aborted) stop();
            });
            previous = start;
            await start;
        },
    };
})();
