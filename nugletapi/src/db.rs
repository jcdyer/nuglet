use rusqlite::{Connection, Rows, NO_PARAMS};

use super::FlickrImage;


pub(super) fn get_images(conn: &Connection) -> Result<Vec<FlickrImage>, Box<std::error::Error>> {
    let mut stmt = conn.prepare("SELECT nsid, url, favorites FROM photo")?;
    let mut rows = stmt.query(NO_PARAMS)?;
    from_rows(&mut rows)
}

pub(super) fn get_images_by_vote(
    conn: &Connection,
    votes: u32,
) -> Result<Vec<FlickrImage>, Box<std::error::Error>> {
    let mut stmt = conn.prepare("SELECT nsid, url, favorites FROM photo WHERE favorites = ?")?;
    let mut rows = stmt.query(&[votes])?;
    from_rows(&mut rows)
}

fn from_rows(rows: &mut Rows) -> Result<Vec<FlickrImage>, Box<std::error::Error>> {
    let mut images = Vec::new();
    while let Some(row) = rows.next() {
        let row = row?;
        images.push(FlickrImage::new(
            row.get::<usize, String>(0),
            row.get::<usize, String>(1).parse()?,
            row.get::<usize, u32>(2),
        ));;
    }
    Ok(images)
}
