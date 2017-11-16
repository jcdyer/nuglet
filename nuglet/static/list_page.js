

// sleep time expects milliseconds
function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}

function fetchResults(app, votes, page) {
    const xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == XMLHttpRequest.DONE && this.status == 200) {
            const response = JSON.parse(this.responseText);
            app.results = app.results.concat(response.results)
        }
    };
    xmlhttp.open("GET", '/api/favorites/' + votes || '' + '?page=' + page);
    xmlhttp.send();
}

function fetchMembers(app) {
    const membersxmlhttp = new XMLHttpRequest();
    membersxmlhttp.onreadystatechange = function() {
        if (this.readyState == XMLHttpRequest.DONE && this.status == 200) {
            const response = JSON.parse(this.responseText);
            app.members = response.members;
        }
    };
    membersxmlhttp.open("GET", '/api/members');
    membersxmlhttp.send();
}

//function vueInit() {
    Vue.component('photo', {
        props: ['members', 'result'],
        template: '<div class="photo"> <h3>{{ result.title }}</h3> <div>{{ members[result.owner] }} | {{ result.date }} | Favs: {{ result.favorites }}</div> <img v-bind:alt="result.title" v-bind:src="result.url" width="600"> </div>'
    });

    const app = new Vue({
        el: '#app',
        data: {
            results: [],
            members: {},
        }
    });

    const body = document.getElementsByTagName('body')[0];
    fetchResults(app, body.dataset.votes, body.dataset.page);
    fetchMembers(app);
//}
