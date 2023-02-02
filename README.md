# RSfsTR
Facial salience from transformer representations. Can be used for facial recognition.


This project is an experimental facial similarity software designed for use with RSvIDX. 

The general architecture is:

```
  Nx(Transformer Encoders) -> Autoencoder((Encoder MLP) -> (Decoder MLP))
```
