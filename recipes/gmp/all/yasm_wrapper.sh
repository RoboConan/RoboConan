#!/usr/bin/env bash
asmopts=()
setoutput=
calculated_output=
source=
while test $# -gt 0; do
    case "$1" in
        *.s | *.S | *.asm | *.ASM)
            calculated_output=$(echo -n "$1" | sed -e 's/\.asm$/.obj/g' | sed -e 's/\.ASM/.obj/g' | sed -e 's/\.s/.obj/g' | sed -e 's/\.S/.obj/g')
            source="$1"
            ;;
        -o)
            asmopts+=("$1")
            shift
            setoutput="$1"
            asmopts+=("$1")
            ;;
        -O*)
            ;;
        -MT | -MD | -MTd | -MDd)
            ;;
        -D*)
            asmopts+=("$1")
            ;;
        *)
            asmopts+=("$1")
            ;;
    esac
    shift
done

if [ "$setoutput" == "" ] && [ "$calculated_output" != "" ]; then
    asmopts+=("-o")
    asmopts+=("$calculated_output")
fi

echo "Executing yasm ${asmopts[@]} $source"
exec yasm ${asmopts[@]} "$source"
