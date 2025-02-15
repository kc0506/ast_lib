from typing import Literal, NamedTuple, TypedDict, Unpack, overload

from .nodes import *


class _Todo: ...


class NameDefaultPair(NamedTuple):
    arg: arg
    value: expr | None


class SlashWithDefault(NamedTuple):
    plain_names: list[arg]
    names_with_defaults: list[NameDefaultPair]


class StarEtc(NamedTuple):
    vararg: arg | None
    kwonlyargs: list[NameDefaultPair]
    kwarg: arg | None


class ArgumentsProps(TypedDict, total=False):
    slash_without_default: list[arg]
    slash_with_default: SlashWithDefault
    plain_names: list[arg]
    names_with_default: list[NameDefaultPair]
    star_etc: StarEtc | None


def _get_args(default_pairs: list[NameDefaultPair]) -> list[arg]:
    return [pair.arg for pair in default_pairs]


@overload
def _get_defaults(
    default_pairs: list[NameDefaultPair], assert_not_none: Literal[True]
) -> list[expr]: ...


@overload
def _get_defaults(
    default_pairs: list[NameDefaultPair], assert_not_none: Literal[False]
) -> list[expr | None]: ...


def _get_defaults(default_pairs: list[NameDefaultPair], assert_not_none: bool):
    if assert_not_none:
        ret = [pair.value for pair in default_pairs if pair.value is not None]
        assert len(ret) == len(default_pairs)
    else:
        ret = [pair.value for pair in default_pairs]
    return ret


def make_arguments(**props: Unpack[ArgumentsProps]) -> arguments:
    posonlyargs: list[arg] = []
    pos_args: list[arg] = []
    pos_defaults: list[expr] = []

    if slash_without_default := props.get("slash_without_default"):
        posonlyargs = slash_without_default
    elif slash_with_default := props.get("slash_with_default"):
        posonlyargs = slash_with_default.plain_names + _get_args(
            slash_with_default.names_with_defaults
        )
        pos_defaults.extend(_get_defaults(slash_with_default.names_with_defaults, True))

    if plain_names := props.get("plain_names"):
        pos_args.extend(plain_names)
    if names_with_default := props.get("names_with_default"):
        pos_args.extend(_get_args(names_with_default))
        pos_defaults.extend(_get_defaults(names_with_default, True))

    vararg = kwarg = None
    kwonlyargs: list[arg] = []
    kwonly_defaults: list[expr | None] = []
    if star_etc := props.get("star_etc"):
        vararg = star_etc.vararg
        kwonlyargs = _get_args(star_etc.kwonlyargs)
        kwonly_defaults = _get_defaults(star_etc.kwonlyargs, False)
        kwarg = star_etc.kwarg

    return arguments(
        posonlyargs=posonlyargs,
        args=pos_args,
        defaults=pos_defaults,
        vararg=vararg,
        kwonlyargs=kwonlyargs,
        kw_defaults=kwonly_defaults,
        kwarg=kwarg,
    )


__all__ = (
    "_Todo",
    "SlashWithDefault",
    "StarEtc",
    "NameDefaultPair",
    "make_arguments",
)
