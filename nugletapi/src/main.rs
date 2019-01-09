use actix_web::{server, App, HttpRequest, Json, Responder};
use actix_web::middleware::cors::Cors;
use http::Uri;
use rusqlite::Connection;
use serde_derive::Serialize;
use serde_json;

mod uri_serde {
    use http::Uri;
    use serde::Serializer;

    pub(super) fn serialize_uri<S>(uri: &Uri, ser: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        ser.serialize_str(&format!("{}", uri))
    }
}

#[derive(Serialize)]
struct FlickrImage {
    nsid: String,
    #[serde(serialize_with = "uri_serde::serialize_uri")]
    uri: Uri,
    votes: u32,
    caption: String,
}

impl FlickrImage {
    fn new(nsid: String, uri: Uri, votes: u32, caption: String) -> FlickrImage {
        FlickrImage { nsid, uri, votes, caption }
    }
}

mod db;

fn greet(req: &HttpRequest) -> impl Responder {
    let to = req.match_info().get("name").unwrap_or("world");
    format!("Hello {}!", to)
}

fn images(req: &HttpRequest) -> impl Responder {
    let conn = Connection::open("../data/nuglet2018.db").unwrap();
    let images = match req.match_info().get("votes") {
        None => db::get_images(&conn),
        Some(n) => db::get_images_by_vote(&conn, n.parse().unwrap()),
    };
    "Access-Control-Allow-Origin: *";
    Json(images.unwrap())
}


fn main() {
    server::new(|| {
        App::new()
            .middleware(Cors::build().allow_origin("All").finish())
            .resource("/", |r| r.f(greet))
            .resource("/im", |r| r.f(images))
            .resource("/im/{votes}", |r| r.f(images))
            .resource("/{name}", |r| r.f(greet))
    }).bind("127.0.0.1:8000")
        .expect("Can not bind to port 8000")
        .run();
}
