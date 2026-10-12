#include <stdio.h>
#include <vorbis/vorbisenc.h>
#include <vorbis/vorbisfile.h>

int main(){
  vorbis_comment   vc;
  vorbis_comment_init(&vc);
  long (*streams)(OggVorbis_File *) = ov_streams;
  (void)streams;
}
