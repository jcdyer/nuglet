import React, { Component } from 'react';
import logo from './logo.svg';
import {toPhoto, Photo} from './photo';
import './App.css';

class Image {
  constructor(public url: URL, public caption: String, public votes: Number) {}
}

interface ImageTileProps {
  image: Photo,
  selected: boolean,
  onClick: (img: Photo) => void,
}

function ImageTile(props: ImageTileProps) {
  return (
    <li className={"image-tile " + props.selected ? "selected" : ""} onClick={() => props.onClick(props.image)}>
      <img
        src={props.image.uri}
      />
      <p>{props.image.caption}</p>
    </li>
  );
}

interface ImageListState {
  selected: Array<Photo>,
  images: Array<Photo>,
}

class ImageList extends Component<{}, ImageListState> {
  constructor(props: {}) {
    super(props);
    this.state = {
      selected: new Array(),
      images: new Array(),
    };
  }

  render() {
    return (
      <ul className="image-list">
      {this.state.images.map((img, idx) =>
        <ImageTile key={img.uri} image={img} selected={this.state.selected.some((x) => x.uri === img.uri)} onClick={() => this.handleClick(img)}/>
      )}
      </ul>
    )
  }

  componentDidMount() {
    fetch("http://localhost:8000/im")
      .then((resp: Response) => resp.text())
      .then((text) => {
        const images = toPhoto(text);
        console.log("fetcht", images);
        this.setState({images})
      })
  }

  handleClick(image: Photo) {
    console.log("handling click of ", image);
    const selected = this.state.selected.slice();
    console.log("PRESELECTED", selected)
    if (selected.some((el) => el.uri === image.uri)) {
      console.log("included");
      this.setState({selected: selected.filter((x) => x.uri != image.uri)});
    } else {
      console.log("not included");
      this.setState({selected: selected.concat(image)});
    }
    console.log(this.state.selected)
  }
}

class App extends Component {
  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <p>
            Edit <code>src/App.tsx</code> and save to reload.
          </p>
          <a
            className="App-link"
            href="https://reactjs.org"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn React
          </a>
        </header>
        <ImageList/>
      </div>
    );
  }
}

export default App;
