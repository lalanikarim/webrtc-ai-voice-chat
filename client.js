let state = {
    pc:null,
    dc:null,
    stream:null,
}

let connectionStatus = document.querySelector("span#connectionStatus")
let wave = document.querySelector("div.wave")
let processing = document.querySelector("div.processing")
let messagesContainer =  document.querySelector("div#messagesContainer")
let chatNameContainer = document.querySelector("div.chat-container .user-bar .name")
let powerButton =  document.querySelector("button#power")
let presetsSelect = document.querySelector("select#presets")
let modelsSelect = document.querySelector("select#models")
let startRecordDiv = document.querySelector("div.circle.start")
let stopRecordDiv = document.querySelector("div.circle.stop")
let waitRecordDiv = document.querySelector("div.circle.wait")

function getcconnectionstatus() {
    let status = "closed"
    if (state.pc) {
        status = state.pc.connectionState
    }
    connectionStatus.textContent = status
}

function negotiate() {
    //pc.addTransceiver('audio', { direction: 'sendrecv' });
    return state.pc.createOffer().then((offer) => {
        return state.pc.setLocalDescription(offer);
    }).then(() => {
        // wait for ICE gathering to complete
        return new Promise((resolve) => {
            if (state.pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (state.pc.iceGatheringState === 'complete') {
                        state.pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                state.pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        var offer = state.pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then((response) => {
        return response.json();
    }).then((answer) => {
        return state.pc.setRemoteDescription(answer);
    }).catch((e) => {
        alert(e);
    });
}

function start() {
    stop()

    const config = {
        sdpSemantics: 'unified-plan'
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    state.pc = new RTCPeerConnection(config);
    state.pc.onconnectionstatechange = (ev) => {
        getcconnectionstatus()
    }
    state.dc = state.pc.createDataChannel("chat")
    state.dc.onopen = (ev) => {
        console.log("Data channel is open and ready to use");
        state.dc.send("Hello server");
    }
    state.dc.onmessage = (ev) => {
        console.log('Received message: ' + ev.data);
        if(ev.data === "ready") {
            record()
        }
        if(ev.data.startsWith("Human:") || ev.data.startsWith("AI:")) {
            logmessage(ev.data)
        }
        if(ev.data.startsWith("playing:")) {
            if(!ev.data.endsWith("silence")) {
                hideElement(processing)
                showElement(wave)
            } else {
                hideElement(wave)
                hideElement(waitRecordDiv)
                showElement(startRecordDiv)
            }
        }
    }
    state.dc.onclose = () => {
        console.log("Data channel is closed");
    }

    // connect audio / video
    state.pc.ontrack = (ev) => {
        console.log('Received remote stream');
        document.querySelector('audio#remoteAudio').srcObject = ev.streams[0];
    }
    // Adding tracks
    // stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
    // document.querySelector('button#start').style.display = 'none';
    //negotiate()
    getMedia()
    showElement(chatNameContainer)
    showElement(presetsSelect)
    showElement(modelsSelect)
    showElement(messagesContainer)
    showElement(startRecordDiv)
    hideElement(waitRecordDiv)
    //document.querySelector('button#stop').style.display = 'inline-block';
}
function logmessage(message) {
    let log = document.querySelector("div.conversation-container")
    let splits = message.split(": ")
    if (splits.length > 1) {
        let messageText = splits.slice(1).join(": ")
        if (messageText.trim().length > 0) {
            let newMessage = document.createElement("div")
            newMessage.classList.add("message")
            if (splits[0] === "AI") {
                newMessage.classList.add("received")
            } else {
                newMessage.classList.add("sent")
            }
            newMessage.textContent = messageText
            log.appendChild(newMessage)
            log.scrollTop = log.scrollHeight
        }
    }
}
function getMedia(){
    const constraints = {
        audio: true,
        video: false
    };
    navigator.mediaDevices
        .getUserMedia(constraints)
        .then(handleSuccess)
        .catch(handleFailure);
}

function stop() {
    hideElement(startRecordDiv)
    showElement(waitRecordDiv)
    hideElement(chatNameContainer)
    hideElement(presetsSelect)
    hideElement(modelsSelect)
    if(state.pc) {
        // close peer connection
        setTimeout(() => {
            state.pc.close();
            getcconnectionstatus()
            state = {pc:null, dc:null, stream:null}
        }, 500);
    }
}

function record(){
    hideElement(wave)
    hideElement(startRecordDiv)
    showElement(stopRecordDiv)
    //getMedia()
    state.dc.send("start_recording")
}

function stopRecord() {
    state.dc.send("stop_recording")
    showElement(processing)
    hideElement(stopRecordDiv)
    showElement(waitRecordDiv)
}
function getResponse(){
    state.dc.send("get_response")
}
function getSilence(){
    state.dc.send("get_silence")
}
function handleSuccess(stream) {
    const tracks = stream.getAudioTracks()
    console.log("Received: ", tracks.length, " tracks")
    state.stream = stream
    state.stream.getAudioTracks().forEach((track) =>{
        state.pc.addTrack(track)
    })
    negotiate()
}

function handleFailure(error) {
    console.log('navigator.getUserMedia error: ', error);
}

function showElement(element) {
    element.classList.remove("d-none")
}
function hideElement(element) {
    element.classList.add("d-none")
}

function changePreset(){
    let preset = document.querySelector("select#presets").value
    state.dc.send("preset:" + preset)
}
function changeModel() {
    let model = document.querySelector("select#models").value
    state.dc.send("model:" + model)
    chatNameContainer.textContent = model
}

document.addEventListener('DOMContentLoaded', () => {
    getcconnectionstatus()
    powerButton.onclick = () => {
        if(state.pc && state.pc.connectionState === "connected") {
            stop()
            powerButton.classList.remove("text-danger")
            powerButton.classList.add("text-success")
        } else {
            start()
            powerButton.classList.remove("text-success")
            powerButton.classList.add("text-danger")
        }
    }
})