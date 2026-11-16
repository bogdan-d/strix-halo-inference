type MemoryUsage = {used: number; total: number};
type SystemMetrics = {
    gpu_percent: number|null;
    cpu_temperature_c: number|null;
    gpu_temperature_c: number|null;
    power_w: number|null;
    ram: MemoryUsage|null;
    gtt: MemoryUsage|null;
    swap: MemoryUsage|null;
};


interface Window {
 __TAURI__?: {core: {invoke<T>(command:string,args?:Record<string,unknown>):Promise<T>; Channel: new<T>() => {onmessage:(message:T)=>void}}};
 inferenceTransport?: {state():Promise<State>; action(path:string):Promise<Response>; logs(source:string,signal:AbortSignal,write:(text:string)=>void):Promise<void>};
}
