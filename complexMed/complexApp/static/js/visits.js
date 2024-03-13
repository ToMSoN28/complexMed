function myFunction() {
  alert("Hello from a static file!");
}

function cardColorRec(visit) {
    const jsNow = new Date();
    const jsFormattedDate = jsNow.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    const jsFormattedTime = jsNow.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    var result = null;
    if (visit.date < jsFormattedDate) {
        result = "#343a40";
    }
    else if (visit.date === jsFormattedDate && visit.start_time < jsFormattedTime) {
        result = "#343a40";
    }
    else if (visit.patient === null) {
        result = '#0d503c';
    } else {
        result = '#664d03';
    }
    return result;
}
