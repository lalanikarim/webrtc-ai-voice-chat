let state = {
    pc:null,
    dc:null,
    stream:null,
}

let startSessionButton = document.querySelector("button#start");
let startRecordingButton = document.querySelector("button#record");
let stopRecordingButton = document.querySelector("button#stopRecord");
let stopSessionButton = document.querySelector("button#stop");

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
    hideElement(startSessionButton)
    showElement(startRecordingButton)
    showElement(stopSessionButton)
    //document.querySelector('button#stop').style.display = 'inline-block';
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
    hideElement(stopSessionButton)
    hideElement(startRecordingButton)
    showElement(startSessionButton)
    if(state.pc) {
        // close peer connection
        setTimeout(() => {
            state.pc.close();
        }, 500);
    }
}

function record(){
    hideElement(startRecordingButton)
    showElement(stopRecordingButton)
    hideElement(stopSessionButton)
    //getMedia()
    state.dc.send("start_recording")
}

function stopRecord() {
    hideElement(stopRecordingButton)
    showElement(startRecordingButton)
    showElement(stopSessionButton)
    state.dc.send("stop_recording")
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
    element.classList.remove("hide")
    element.classList.add("show")
}
function hideElement(element) {
    element.classList.remove("show")
    element.classList.add("hide")
}
