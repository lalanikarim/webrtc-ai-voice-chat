let pc = null;
let dc = null;

function negotiate() {
    //pc.addTransceiver('audio', { direction: 'sendrecv' });
    return pc.createOffer().then((offer) => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        // wait for ICE gathering to complete
        return new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        var offer = pc.localDescription;
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
        return pc.setRemoteDescription(answer);
    }).catch((e) => {
        alert(e);
    });
}

function start(stream) {
    const config = {
        sdpSemantics: 'unified-plan'
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    pc = new RTCPeerConnection(config);
    dc = pc.createDataChannel("chat")
    dc.onopen = (ev) => {
        console.log("Data channel is open and ready to use");
        dc.send("Hello server");
    }
    dc.onmessage = (ev) => {
        console.log('Received message: ' + ev.data);
    }
    dc.onclose = () => {
        console.log("Data channel is closed");
    }

    // connect audio / video
    pc.ontrack = (ev) => {
        console.log('Received remote stream');
        document.querySelector('audio#remoteAudio').srcObject = ev.streams[0];
    }
    // Adding tracks
    stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
    //document.querySelector('button#start').style.display = 'none';
    negotiate();
    //document.querySelector('button#stop').style.display = 'inline-block';
}

function stop() {
    document.querySelector('button#stop').style.display = 'none';
    //document.querySelector('button#start').style.display = 'inline-block';
    // close peer connection
    setTimeout(() => {
        pc.close();
    }, 500);
}

function record(){
    document.querySelector('button#record').style.display = 'none';
    document.querySelector('button#stopRecord').style.display = 'inline-block';
    const constraints = {
        audio: true,
        video: false
    };
    navigator.mediaDevices
        .getUserMedia(constraints)
        .then(handleSuccess)
        .catch(handleFailure);
}

function handleSuccess(stream) {
    const tracks = stream.getAudioTracks()
    console.log("Received: ", tracks.length, " tracks")
    start(stream)
}

function handleFailure(error) {
    console.log('navigator.getUserMedia error: ', error);
}

function stopRecord() {
    document.querySelector('button#stopRecord').style.display = 'none';
    document.querySelector('button#record').style.display = 'inline-block';
    stop()
}
