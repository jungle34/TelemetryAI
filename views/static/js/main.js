async function startTelemetryHandler() {
    await window.pywebview.api.startTelemetryUDP()
}

function getTelemetryStatus() {
    telemetryStatus()
        .then((response)=>{
            let _value = response===true?"Telemetria Online":"Telemetria Offline";
            let _class = response===true?"badge text-bg-success":"badge text-bg-danger";
            
            $("#status_telemetry").html(_value).attr("class", _class);
        });
}

async function telemetryStatus() {
    let response = await window.pywebview.api.getTelemetryUdpStatus();
    
    return response;
}


async function getModule(module) {
    let response = await window.pywebview.api.getModule(module);

    return response;
}

function setModule(module) {    
    getModule(module)
        .then((response)=>{
            $('#main-content').html(response);
        });
}